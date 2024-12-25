#define PY_Suint64_t_CLEAN
#include <inttypes.h>
#include <string.h>
#include <Python.h>
#include "hashmap.c/hashmap.h"


// Contains a pointer to an array element and a reference to the stride
struct elem {
    void* p_elem;
    uint64_t stride;
};

typedef struct hashmap hashmap;

uint64_t hash(const void *elem, uint64_t seed0, uint64_t seed1) {
    const struct elem *e = elem;
    return hashmap_murmur(e->p_elem, e->stride, seed0, seed1);
}

int compare(const void *elem1, const void *elem2, void *udata) {
    // Compares two array elements
    const struct elem *e1 = elem1;
    const struct elem *e2 = elem2;
    return memcmp(e1->p_elem, e2->p_elem, e1->stride);
}

static PyObject *unique(PyObject *self, PyObject *args) {
    /* Do NOT use int, long, size_t etc., as these can cause cross-platform issues.
    See https://stackoverflow.com/questions/7456902/long-vs-int-c-c-whats-the-point. */
    void *array;
    int64_t ndim;
    int64_t *dimensions, *strides;
    int64_t *index, *inverse, *counts;
    if (!PyArg_ParseTuple(args, "LkLLLLL", &array, &ndim, &dimensions, &strides, &index, &inverse, &counts))
        return NULL;

    uint64_t n = dimensions[0];
    uint64_t stride = strides[0];
    hashmap *map = hashmap_new(sizeof(struct elem*), 0, 0, 0, hash, compare, NULL, NULL);

    uint64_t n_unique = 0;
    for (uint64_t i = 0; i < n; ++ i) {
        // Construct element
        struct elem this_elem = {
            .p_elem = (char*)array + stride * i,
            .stride = stride,
        };
        // Check if already in map
        struct elem *p_found_elem = hashmap_get(map, &this_elem);
        if (p_found_elem != NULL) {
            // Get index of found element by difference in memory address
            uint64_t found_index = ((char*)(p_found_elem->p_elem) - (char*)array) / stride;
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

/* Module declaration */
static PyMethodDef _pelutils_c_methods[] = {
    { "unique", unique, METH_VARARGS, NULL },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef _pelutils_c_module = {
    PyModuleDef_HEAD_INIT,
    "_pelutils_c", NULL, -1, _pelutils_c_methods
};

PyMODINIT_FUNC PyInit__pelutils_c(void) {
    PyObject *module = PyModule_Create(&_pelutils_c_module);
    return module;
}
