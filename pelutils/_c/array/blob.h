#ifndef BLOB_H
#define BLOB_H

#include <stdlib.h>

#include <Python.h>

#include "../deque/deque.h"
#include "../hashmap/hashmap.h"
#include "../types.h"


struct node_t {
    // ndim long array of representing a single coordinate in the grid
    i64 *grid_coord_p;
    // Index in the sparse grid coordinate array
    i64 index;
    // Number of dimensions in the grid
    i64 ndim;
};
typedef struct node_t node_t;


PyObject *build_lookup_table(PyObject *self, PyObject *args);
PyObject *free_lookup_table(PyObject *self, PyObject *args);
PyObject *find_blob(PyObject *self, PyObject *args);

#endif
