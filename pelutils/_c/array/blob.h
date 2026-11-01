#ifndef BLOB_H
#define BLOB_H

#include <stdlib.h>

#include <Python.h>

#include "../deque/deque.h"
#include "../hash/hash.h"
#include "../types.h"


PyObject *build_lookup_table(PyObject *self, PyObject *args);
PyObject *free_lookup_table(PyObject *self, PyObject *args);
PyObject *find_blob(PyObject *self, PyObject *args);

#endif
