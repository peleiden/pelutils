#include "blob.h"

// Marks a slot that has never held a coordinate, which is what ends a probe
#define EMPTY_SLOT (-1)
// Marks a slot whose coordinate has been visited. It must not end a probe, as later coordinates may have probed past it.
#define CLAIMED_SLOT (-2)


// Open addressing table with linear probing. Slots refer to coordinates by their row in the index array.
typedef struct {
    u64 hash;   // Stored to avoid most coordinate comparisons
    i64 index;  // Row in the index array, EMPTY_SLOT, or CLAIMED_SLOT
} slot_t;

typedef struct {
    slot_t *slots;
    u64 mask;   // Number of slots minus one. The number of slots is a power of two, so hash & mask is a valid position.
} table_t;

// Returns the slot with the given coordinates, or if there is none, the empty slot where they belong. The table is
// never full, so an empty slot always exists.
static inline slot_t *table_probe(const table_t *table, const i64 *index_array, const i64 *coord, i64 ndim, u64 hash) {
    u64 pos = hash & table->mask;
    while (table->slots[pos].index != EMPTY_SLOT) {
        slot_t *slot = &table->slots[pos];
        // Equal hashes do not guarantee equal coordinates, so the coordinates must be compared as well
        if (slot->index != CLAIMED_SLOT && slot->hash == hash
            && memcmp(index_array + slot->index * ndim, coord, ndim * sizeof(*coord)) == 0)
            return slot;
        pos = (pos + 1) & table->mask;
    }
    return &table->slots[pos];
}

// Claims the given coordinates, so they can only be found once. Returns their row or EMPTY_SLOT if not in the table.
static inline i64 table_claim(const table_t *table, const i64 *index_array, const i64 *coord, i64 ndim) {
    slot_t *slot = table_probe(table, index_array, coord, ndim, xxh3(coord, ndim * sizeof(*coord), 0));
    i64 index = slot->index;
    if (index != EMPTY_SLOT)
        slot->index = CLAIMED_SLOT;
    return index;
}

/* For a given set of coordinates, wrap them by modulating with the axis size.

`grid_coord_p` and `wrap_axis_sizes` are both `ndim` long. For axes where `wrap_axis_sizes`
is 0, the grid coordinates remain unchanged. */
static void cond_wrap(i64 *grid_coord_p, u64 *wrap_axis_sizes, long long ndim) {
    for (long long j = 0; j < ndim; ++ j) {
        i64 mod = (i64)wrap_axis_sizes[j];
        if (mod != 0) {
            grid_coord_p[j] = ((grid_coord_p[j] % mod) + mod) % mod;
        }
    }
}

PyObject *build_lookup_table(PyObject *self, PyObject *args) {
    void **pointers;
    // Length ndim
    u64 *wrap_axis_sizes;
    // Shape num_indices x ndim
    i64 *index_array;
    long long num_indices;
    long long ndim;

    if (!PyArg_ParseTuple(args, "KKKKK", &pointers, &wrap_axis_sizes, &index_array, &num_indices, &ndim))
        return NULL;

    // free_lookup_table is also called if building the table fails
    pointers[0] = NULL;

    // Prevents the number of slots and their size in bytes from overflowing
    if ((u64)num_indices > SIZE_MAX / sizeof(slot_t) / 4)
        return PyErr_NoMemory();
    // The number of coordinates is known and never increases, so the table does not need to grow and stays at most half full
    u64 n_slots = 16;
    while (n_slots < 2 * (u64)num_indices)
        n_slots *= 2;

    table_t *table = malloc(sizeof(*table));
    slot_t *slots = malloc(n_slots * sizeof(*slots));
    if (table == NULL || slots == NULL) {
        free(table);
        free(slots);
        return PyErr_NoMemory();
    }
    for (u64 i = 0; i < n_slots; ++ i)
        slots[i].index = EMPTY_SLOT;
    table->slots = slots;
    table->mask = n_slots - 1;
    pointers[0] = table;

    for (long long i = 0; i < num_indices; ++ i) {
        i64 *coord = index_array + i * ndim;
        cond_wrap(coord, wrap_axis_sizes, ndim);
        u64 hash = xxh3(coord, ndim * sizeof(*coord), 0);
        // For duplicate coordinates, the last row is the one that can be found
        slot_t *slot = table_probe(table, index_array, coord, ndim, hash);
        slot->hash = hash;
        slot->index = i;
    }

    Py_RETURN_NONE;
}

PyObject *free_lookup_table(PyObject *self, PyObject *args) {
    void **pointers;

    if (!PyArg_ParseTuple(args, "K", &pointers))
        return NULL;

    table_t *table = pointers[0];
    if (table != NULL) {
        free(table->slots);
        free(table);
    }

    Py_RETURN_NONE;
}

PyObject *find_blob(PyObject *self, PyObject *args) {
    void **pointers;
    // Length ndim
    u64 *wrap_axis_sizes;
    // Shape num_indices x ndim
    i64 *index_array;
    // Row of index_array to start the search from
    long long start_index;
    long long num_indices;
    long long ndim;
    // Rows in index_array belonging to the blob are stored here
    PyObject *blob_indices_list;
    // See format specifiers at https://docs.python.org/3.11/c-api/arg.html#strings-and-buffers
    if (!PyArg_ParseTuple(args, "KKKKKKO!", &pointers, &wrap_axis_sizes, &index_array, &start_index, &num_indices, &ndim, &PyList_Type, &blob_indices_list))
        return NULL;

    table_t *coord_to_index = pointers[0];

    // Do BFS from the given starting row
    deque_t *q = deque_init();
    deque_append_right(q, start_index);
    table_claim(coord_to_index, index_array, index_array + ndim * start_index, ndim);

    // Currently visited node
    i64 v_index;
    // Neighbour of v being checked
    i64 *neighbour_coord = malloc(ndim * sizeof(*neighbour_coord));
    while (q->num_elems > 0) {
        deque_pop_left(q, &v_index);
        i64 *v_coord = &index_array[ndim * v_index];

        // Append the found index to the blob index list
        PyObject *v_index_py_long = PyLong_FromLong(v_index);
        PyList_Append(blob_indices_list, v_index_py_long);
        Py_DECREF(v_index_py_long);

        for (u64 axis = 0; axis < ndim; axis ++) {
            for (i64 direction = -1; direction < 2; direction += 2) {
                memcpy(neighbour_coord, v_coord, ndim * sizeof(*v_coord));
                neighbour_coord[axis] += direction;
                cond_wrap(neighbour_coord, wrap_axis_sizes, ndim);
                i64 neighbour_index = table_claim(coord_to_index, index_array, neighbour_coord, ndim);
                if (neighbour_index != EMPTY_SLOT) {
                    // Neighbour exists, so add it to the queue
                    deque_append_right(q, neighbour_index);
                }
            }
        }
    }

    free(neighbour_coord);
    deque_free(q);

    Py_RETURN_NONE;
}
