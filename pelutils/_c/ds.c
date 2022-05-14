#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include "hashmap.c/hashmap.h"


// Contains a pointer to an array element and a reference to the stride
struct elem {
    void* p_elem;
    size_t stride;
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
    void *array;
    unsigned long ndim;
    unsigned long *dimensions, *strides;
    long *index, *inverse, *counts;
    if (!PyArg_ParseTuple(args, "LkLLLLL", &array, &ndim, &dimensions, &strides, &index, &inverse, &counts))
        return NULL;

    if (inverse == -1)
        inverse = NULL;
    if (counts == -1)
        counts = NULL;

    size_t n = dimensions[0];
    size_t stride = strides[0];
    hashmap *map = hashmap_new(sizeof(struct elem*), 0, 0, 0, hash, compare, NULL, NULL);

    size_t n_unique = 0;
    for (size_t i = 0; i < n; i ++) {
        // Construct element
        struct elem this_elem = {
            .p_elem = (char*)array + stride * i,
            .stride = stride,
        };
        // Check if already in map
        struct elem *p_found_elem = hashmap_get(map, &this_elem);
        if (p_found_elem != NULL) {
            // Get index of found element by difference in memory address
            size_t found_index = ((char*)(p_found_elem->p_elem) - (char*)array) / stride;
            if (inverse != NULL)
                inverse[i] = inverse[found_index];
            if (counts != NULL)
                counts[found_index] ++;
        } else {
            // Set new element in hashmap
            hashmap_set(map, &this_elem);
            index[n_unique] = i;
            if (inverse != NULL)
                inverse[i] = n_unique;
            if (counts != NULL)
                counts[i] = 1;
            n_unique ++;
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
