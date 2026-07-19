#include "unique.h"


// Contains a pointer to an array element and a reference to the stride
struct elem {
    void* p_elem;
    u64 stride;
};



static u64 hash(const void *elem, u64 seed0, u64 seed1) {
    const struct elem *e = elem;
    return hashmap_murmur(e->p_elem, e->stride, seed0, seed1);
}

static int compare(const void *elem1, const void *elem2, void *udata) {
    // Compares two array elements
    const struct elem *e1 = elem1;
    const struct elem *e2 = elem2;
    return memcmp(e1->p_elem, e2->p_elem, e1->stride);
}

PyObject *unique(PyObject *self, PyObject *args) {
    /* Do NOT use int, long, size_t etc., as these can cause cross-platform issues.
    See https://stackoverflow.com/questions/7456902/long-vs-int-c-c-whats-the-point. */
    void *array;
    i64 ndim;
    i64 *dimensions, *strides;
    i64 *index, *inverse, *counts;
    if (!PyArg_ParseTuple(args, "LkLLLLL", &array, &ndim, &dimensions, &strides, &index, &inverse, &counts))
        return NULL;

    u64 n = dimensions[0];
    u64 stride = strides[0];
    hashmap *map = hashmap_new(sizeof(struct elem*), 0, 0, 0, hash, compare, NULL, NULL);

    u64 n_unique = 0;
    for (u64 i = 0; i < n; ++ i) {
        // Construct element
        struct elem this_elem = {
            .p_elem = (char*)array + stride * i,
            .stride = stride,
        };
        // Check if already in map
        struct elem *p_found_elem = hashmap_get(map, &this_elem);
        if (p_found_elem != NULL) {
            // Get index of found element by difference in memory address
            u64 found_index = ((char*)(p_found_elem->p_elem) - (char*)array) / stride;
            if (inverse != NULL)
                inverse[i] = inverse[found_index];
            if (counts != NULL)
                ++ counts[found_index];
        } else {
            // Set new element in hashmap
            hashmap_set(map, &this_elem);
            index[n_unique] = i;
            if (inverse != NULL)
                inverse[i] = n_unique;
            if (counts != NULL)
                counts[i] = 1;
            ++ n_unique;
        }
    }
    hashmap_free(map);
    return PyLong_FromSize_t(n_unique);
}



