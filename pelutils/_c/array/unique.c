// Finds the unique elements of an array in linear time. An element is a fixed-size run of bytes, and two elements are
// equal if their bytes are equal. Every result is built around an element's first index, the index of the first element
// with the same bytes, which gives results in order of first occurrence regardless of the method used. There are three:
//
// - unique_lookup: A table with an entry per possible value, for 1-byte elements and for 2-byte elements in large arrays.
// - unique_hashed: A hash table, for everything else on a single thread.
// - unique_parallel: One hash table per thread, each holding its own share of the distinct elements.
//
// The caller owns all arrays and must make sure that index, inverse, and counts have room for n elements. inverse and
// counts are optional and may be NULL. counts is indexed by first index, so entries at other indices are left unset.

#include "unique.h"

#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <process.h>
    #include <windows.h>
#else
    #include <pthread.h>
#endif

// Arrays with 2-byte elements use a direct lookup table from this size. Below it, the table's cost is not worthwhile.
#define MIN_SIZE_FOR_U16_LOOKUP (1ULL << 14)
// Upper limit for the number of slots a hash table starts with. Tables with many elements reach their size by growing.
#define INITIAL_TABLE_SLOTS (1ULL << 10)
// Marks an unused entry in a hash table or lookup table. Cannot be mistaken for a first index, as these are not
// negative.
#define EMPTY_SLOT (-1)
// Returned instead of a first index or number of unique elements if memory could not be allocated
#define ALLOC_FAILED (-1)


// Open addressing table with linear probing. Slots refer to array elements by their first index.
typedef struct {
    u64 hash;   // Stored to avoid most element comparisons and to not rehash when growing
    i64 index;  // First index of the element, or EMPTY_SLOT
} slot_t;

typedef struct {
    slot_t *slots;
    u64 mask;   // Number of slots minus one. The number of slots is a power of two, so hash & mask is a valid position.
    u64 count;  // Number of used slots
} table_t;

// Allocates the slots and marks them as empty. Only sets the fields related to the slots, so that it can also be used
// for growing. On failure, the table is untouched.
static bool table_alloc(table_t *table, u64 n_slots) {
    // Prevents the size in bytes from overflowing
    if (n_slots > SIZE_MAX / sizeof(slot_t))
        return false;
    slot_t *slots = malloc(n_slots * sizeof(slot_t));
    if (slots == NULL)
        return false;
    for (u64 i = 0; i < n_slots; ++ i)
        slots[i].index = EMPTY_SLOT;
    table->slots = slots;
    table->mask = n_slots - 1;
    return true;
}

// Creates a table for an expected n elements. The slots are freed by the caller.
static bool table_init(table_t *table, u64 n) {
    // The table is kept at most half full, so n elements fit in 2n slots. Large n still start small,
    // as there may be far fewer distinct elements than elements, and growing is cheap.
    u64 n_slots = 16;
    while (n_slots < INITIAL_TABLE_SLOTS && n_slots < 2 * n)
        n_slots *= 2;
    table->count = 0;
    return table_alloc(table, n_slots);
}

// Doubles the number of slots. On failure, the table is still valid with its current slots.
static bool table_grow(table_t *table) {
    table_t grown;
    if (!table_alloc(&grown, 2 * (table->mask + 1)))
        return false;
    // All elements are known to be distinct, so each only needs an empty slot and no comparisons
    for (u64 i = 0; i <= table->mask; ++ i) {
        slot_t slot = table->slots[i];
        if (slot.index == EMPTY_SLOT)
            continue;
        u64 pos = slot.hash & grown.mask;
        while (grown.slots[pos].index != EMPTY_SLOT)
            pos = (pos + 1) & grown.mask;
        grown.slots[pos] = slot;
    }
    free(table->slots);
    table->slots = grown.slots;
    table->mask = grown.mask;
    return true;
}

static inline u64 mix64(u64 x) {
    // Finalizer from MurmurHash3. Spreads each input bit to all output bits, which matters as both the
    // low bits (table position) and the high bits (thread partition) of the hash are used.
    x ^= x >> 33;
    x *= 0xff51afd7ed558ccdULL;
    x ^= x >> 33;
    x *= 0xc4ceb9fe1a85ec53ULL;
    x ^= x >> 33;
    return x;
}

// Elements may be unaligned, e.g. in packed structured arrays, so they are always read with memcpy.
static inline u64 hash_elem(const char *p, u64 size) {
    if (size <= sizeof(u64)) {
        // The element fits in an integer, so it only needs mixing. Which bytes of v are
        // set depends on endianness, which is fine, as hashes are only used within a call.
        u64 v = 0;
        memcpy(&v, p, size);
        return mix64(v);
    }
    return hashmap_xxhash3(p, size, 0, 0);
}

// Returns the first index of the element at index i, inserting the element if it is new, in which case the first index
// is i itself. Returns ALLOC_FAILED if the table had to grow but could not.
static inline i64 table_first_index(table_t *table, const char *array, u64 size, u64 i, u64 hash) {
    const char *elem = array + i * size;
    // Probe until either the element or an empty slot is found, the latter meaning that the element is new.
    // The table is never full, so an empty slot always exists.
    u64 pos = hash & table->mask;
    while (table->slots[pos].index != EMPTY_SLOT) {
        const slot_t *slot = &table->slots[pos];
        // Equal hashes do not guarantee equal elements, so the bytes must be compared as well
        if (slot->hash == hash && memcmp(array + (u64)slot->index * size, elem, size) == 0)
            return slot->index;
        pos = (pos + 1) & table->mask;
    }
    // Keep the table at most half full, as probing gets slow when it fills up
    if ((table->count + 1) * 2 > table->mask + 1) {
        if (!table_grow(table))
            return ALLOC_FAILED;
        // Positions change when growing, so the empty slot must be found again
        pos = hash & table->mask;
        while (table->slots[pos].index != EMPTY_SLOT)
            pos = (pos + 1) & table->mask;
    }
    table->slots[pos].hash = hash;
    table->slots[pos].index = (i64)i;
    ++ table->count;
    return (i64)i;
}

// Updates the results with the element at index i given its first index. Elements must be recorded in order of index.
static inline void record_elem(u64 i, i64 first, i64 *n_unique, i64 *index, i64 *inverse, i64 *counts) {
    if (first == (i64)i) {
        // First time the element is seen, so it becomes the next unique element
        index[*n_unique] = first;
        if (inverse != NULL)
            inverse[i] = *n_unique;
        if (counts != NULL)
            counts[i] = 1;
        ++ *n_unique;
    } else {
        // first is earlier than i, so its inverse has already been set
        if (inverse != NULL)
            inverse[i] = inverse[first];
        if (counts != NULL)
            ++ counts[first];
    }
}

// Direct lookup by the element's bytes, for elements small enough that a table of all possible values is cheap.
// The size must be 1 or 2. Called with a constant size in unique_dispatch so that the size branch is compiled away.
static inline i64 unique_lookup(const char *array, u64 n, u64 size, i64 *index, i64 *inverse, i64 *counts) {
    // Maps each possible value of an element to its first index
    u64 n_values = 1ULL << (8 * size);
    i64 *first_indices = malloc(n_values * sizeof(*first_indices));
    if (first_indices == NULL)
        return ALLOC_FAILED;
    for (u64 i = 0; i < n_values; ++ i)
        first_indices[i] = EMPTY_SLOT;
    i64 n_unique = 0;
    for (u64 i = 0; i < n; ++ i) {
        // Read with the element's own width, so that the value stays within the table on any endianness
        u64 value;
        if (size == 1) {
            value = (u8)array[i];
        } else {
            u16 value_u16;
            memcpy(&value_u16, array + i * size, sizeof(value_u16));
            value = value_u16;
        }
        i64 *first = &first_indices[value];
        if (*first == EMPTY_SLOT)
            *first = (i64)i;
        record_elem(i, *first, &n_unique, index, inverse, counts);
    }
    free(first_indices);
    return n_unique;
}

// Single-threaded unique with a hash table. Returns the number of unique elements or ALLOC_FAILED. Called with a constant
// size in unique_dispatch where possible, which allows the compiler to replace memcpy and memcmp with direct loads and
// comparisons.
static inline i64 unique_hashed(const char *array, u64 n, u64 size, i64 *index, i64 *inverse, i64 *counts) {
    table_t table;
    if (!table_init(&table, n))
        return ALLOC_FAILED;
    i64 n_unique = 0;
    for (u64 i = 0; i < n; ++ i) {
        i64 first = table_first_index(&table, array, size, i, hash_elem(array + i * size, size));
        if (first == ALLOC_FAILED) {
            free(table.slots);
            return ALLOC_FAILED;
        }
        record_elem(i, first, &n_unique, index, inverse, counts);
    }
    free(table.slots);
    return n_unique;
}

// Chooses the single-threaded method for the element size. The constant sizes are for the compiler and not
// redundant: Calls to unique_hashed with size as a variable are several times slower for small elements.
static i64 unique_dispatch(const char *array, u64 n, u64 size, i64 *index, i64 *inverse, i64 *counts) {
    switch (size) {
        case 1: return unique_lookup(array, n, 1, index, inverse, counts);
        case 2:
            if (n >= MIN_SIZE_FOR_U16_LOOKUP)
                return unique_lookup(array, n, 2, index, inverse, counts);
            return unique_hashed(array, n, 2, index, inverse, counts);
        case 4: return unique_hashed(array, n, 4, index, inverse, counts);
        case 8: return unique_hashed(array, n, 8, index, inverse, counts);
        default: return unique_hashed(array, n, size, index, inverse, counts);
    }
}

// Hashes elements in [start, stop). Called with a constant size where possible for the same reason as unique_hashed.
static inline void hash_range(const char *array, u64 size, u64 start, u64 stop, u64 *hashes) {
    for (u64 i = start; i < stop; ++ i)
        hashes[i] = hash_elem(array + i * size, size);
}

// Finds the first indices of the elements in a single partition. All equal elements have equal hashes, so they are
// always in the same partition, which means that the partitions can be processed independently with a table each.
// Elements are visited in order of index, so the first index found is correct across the entire array. Only the worker
// owning a partition writes to the positions in first_indices and counts of the partition's elements, so there are no
// data races. Called with a constant size where possible for the same reason as unique_hashed.
static inline bool partition_range(
    const char *array, u64 n, u64 size, const u64 *hashes, u64 partition, u64 n_partitions, i64 *first_indices, i64 *counts
) {
    table_t table;
    // A partition holds about n / n_partitions elements, and the table grows if it holds more
    if (!table_init(&table, n / n_partitions))
        return false;
    for (u64 i = 0; i < n; ++ i) {
        // The table uses the low bits of the hash, so the partition is taken from the high bits to keep the two
        // independent. Scales the top 16 bits from [0, 2^16) to [0, n_partitions) by multiplying and shifting.
        if (((hashes[i] >> 48) * n_partitions) >> 16 != partition)
            continue;
        i64 first = table_first_index(&table, array, size, i, hashes[i]);
        if (first == ALLOC_FAILED) {
            free(table.slots);
            return false;
        }
        first_indices[i] = first;
        if (counts != NULL) {
            if (first == (i64)i)
                counts[i] = 1;
            else
                ++ counts[first];
        }
    }
    free(table.slots);
    return true;
}

#ifdef _WIN32
    typedef HANDLE worker_thread_t;
#else
    typedef pthread_t worker_thread_t;
#endif

// Work for a single thread. Must not use the Python API, as worker threads do not hold the GIL.
typedef struct {
    worker_thread_t handle;
    bool started;     // Whether handle refers to a thread that must be joined
    const char *array;
    u64 n, size;
    u64 thread;       // Number of this thread, which also selects its chunk and partition
    u64 n_threads;
    u64 *hashes;      // Shared between threads. Each thread writes its own chunk.
    i64 *first_indices, *counts;
    bool is_hash_phase;
    bool success;     // Set by the job when done. Must only be read after the job's thread has been joined.
} job_t;

// Does a job's work for the current phase. Runs on either a worker thread or the calling thread.
static void run_job(job_t *job) {
    if (job->is_hash_phase) {
        // Equal chunks, where the last thread takes the remainder
        u64 start = job->n / job->n_threads * job->thread;
        u64 stop = job->thread + 1 == job->n_threads ? job->n : start + job->n / job->n_threads;
        switch (job->size) {
            case 4: hash_range(job->array, 4, start, stop, job->hashes); break;
            case 8: hash_range(job->array, 8, start, stop, job->hashes); break;
            default: hash_range(job->array, job->size, start, stop, job->hashes); break;
        }
        job->success = true;
        return;
    }
    // All hashes are ready at this point, as the phases are separated by joining all threads
    const char *array = job->array;
    switch (job->size) {
        case 4: job->success = partition_range(array, job->n, 4, job->hashes, job->thread, job->n_threads, job->first_indices, job->counts); break;
        case 8: job->success = partition_range(array, job->n, 8, job->hashes, job->thread, job->n_threads, job->first_indices, job->counts); break;
        default: job->success = partition_range(array, job->n, job->size, job->hashes, job->thread, job->n_threads, job->first_indices, job->counts); break;
    }
}

// Minimal wrapper around the native thread APIs, as C11 threads are not available on all supported platforms
#ifdef _WIN32
    static unsigned __stdcall thread_main(void *job) {
        run_job(job);
        return 0;
    }

    static bool thread_start(worker_thread_t *thread, job_t *job) {
        // _beginthreadex rather than CreateThread, as jobs use the C runtime through malloc and free
        *thread = (HANDLE)_beginthreadex(NULL, 0, thread_main, job, 0, NULL);
        return *thread != 0;
    }

    static void thread_join(worker_thread_t thread) {
        WaitForSingleObject(thread, INFINITE);
        CloseHandle(thread);
    }
#else
    static void *thread_main(void *job) {
        run_job(job);
        return NULL;
    }

    static bool thread_start(worker_thread_t *thread, job_t *job) {
        return pthread_create(thread, NULL, thread_main, job) == 0;
    }

    static void thread_join(worker_thread_t thread) {
        pthread_join(thread, NULL);
    }
#endif

// Runs all jobs and waits for them. A job for which no thread can be started runs on the calling thread, so that a lack
// of threads only costs time. Returns whether all jobs succeeded.
static bool run_jobs(job_t *jobs, u64 n_threads) {
    // The calling thread takes the first job itself rather than idling while waiting for the workers
    for (u64 i = 1; i < n_threads; ++ i) {
        jobs[i].started = thread_start(&jobs[i].handle, &jobs[i]);
        if (!jobs[i].started)
            run_job(&jobs[i]);
    }
    run_job(&jobs[0]);
    bool success = jobs[0].success;
    for (u64 i = 1; i < n_threads; ++ i) {
        if (jobs[i].started)
            thread_join(jobs[i].handle);
        success = success && jobs[i].success;
    }
    return success;
}

// Multithreaded unique with the same results as unique_dispatch. Works in three steps:
//
// 1. Each thread hashes a chunk of the elements.
// 2. Each thread finds the first indices of the elements whose hash belongs to its partition, see partition_range.
// 3. A single pass in order of index turns the first indices into results.
//
// Returns the number of unique elements or ALLOC_FAILED.
static i64 unique_parallel(const char *array, u64 n, u64 size, u64 n_threads, i64 *index, i64 *inverse, i64 *counts) {
    // Prevents the sizes in bytes from overflowing
    if (n > SIZE_MAX / sizeof(u64) || n_threads > SIZE_MAX / sizeof(job_t))
        return ALLOC_FAILED;
    // first_indices is finalized into the inverse in place, so it uses the inverse buffer if there is one
    u64 *hashes = malloc(n * sizeof(*hashes));
    i64 *first_indices = inverse != NULL ? inverse : malloc(n * sizeof(*first_indices));
    job_t *jobs = malloc(n_threads * sizeof(*jobs));

    i64 n_unique = ALLOC_FAILED;
    if (hashes != NULL && first_indices != NULL && jobs != NULL) {
        for (u64 i = 0; i < n_threads; ++ i) {
            job_t job = {
                .array = array, .n = n, .size = size, .thread = i, .n_threads = n_threads,
                .hashes = hashes, .first_indices = first_indices, .counts = counts, .is_hash_phase = true,
            };
            jobs[i] = job;
        }
        // Hashing allocates nothing and cannot fail, so the result can be ignored
        run_jobs(jobs, n_threads);
        for (u64 i = 0; i < n_threads; ++ i)
            jobs[i].is_hash_phase = false;
        if (run_jobs(jobs, n_threads)) {
            // Rewrites first_indices into the inverse in place. A first index is never later than the
            // element referring to it, so the position it refers to has already been rewritten.
            n_unique = 0;
            for (u64 i = 0; i < n; ++ i) {
                if (first_indices[i] == (i64)i) {
                    index[n_unique] = (i64)i;
                    first_indices[i] = n_unique;
                    ++ n_unique;
                } else {
                    first_indices[i] = first_indices[first_indices[i]];
                }
            }
        }
    }

    free(hashes);
    if (first_indices != inverse)
        free(first_indices);
    free(jobs);
    return n_unique;
}

// Python signature: unique(array, n, size, n_threads, index, inverse, counts) -> number of unique elements
// All pointers are passed as integers, with 0 for the optional inverse and counts. The array must be C-contiguous with n
// elements of size bytes. n_threads above 1 always runs in parallel, so whether it is worthwhile is up to the caller.
PyObject *unique(PyObject *self, PyObject *args) {
    u64 array, n, size, n_threads, index, inverse, counts;
    // See format specifiers at https://docs.python.org/3.11/c-api/arg.html#strings-and-buffers
    if (!PyArg_ParseTuple(args, "KKKKKKK", &array, &n, &size, &n_threads, &index, &inverse, &counts))
        return NULL;

    const char *p_array = (const char*)(uintptr_t)array;
    i64 *p_index = (i64*)(uintptr_t)index;
    i64 *p_inverse = (i64*)(uintptr_t)inverse;
    i64 *p_counts = (i64*)(uintptr_t)counts;
    // The GIL is deliberately kept, also during parallel work, so Python code cannot modify the array in the meantime
    i64 n_unique = n_threads > 1
        ? unique_parallel(p_array, n, size, n_threads, p_index, p_inverse, p_counts)
        : unique_dispatch(p_array, n, size, p_index, p_inverse, p_counts);
    if (n_unique == ALLOC_FAILED)
        return PyErr_NoMemory();
    return PyLong_FromLongLong(n_unique);
}

// Python signature: unique_groups(n, inverse, starts, order) -> None
// Writes the indices of the elements to order, grouped by unique element and ascending within each group. All pointers
// are passed as integers. starts must hold the position in order at which each group starts and is overwritten.
PyObject *unique_groups(PyObject *self, PyObject *args) {
    u64 n, inverse, starts, order;
    if (!PyArg_ParseTuple(args, "KKKK", &n, &inverse, &starts, &order))
        return NULL;

    // Stable counting sort. starts is used as the next write position of each group.
    const i64 *p_inverse = (const i64*)(uintptr_t)inverse;
    i64 *p_starts = (i64*)(uintptr_t)starts;
    i64 *p_order = (i64*)(uintptr_t)order;
    // Visiting elements in order of index keeps each group ascending
    for (u64 i = 0; i < n; ++ i)
        p_order[p_starts[p_inverse[i]] ++] = (i64)i;
    Py_RETURN_NONE;
}
