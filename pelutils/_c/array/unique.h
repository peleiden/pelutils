#ifndef UNIQUE_H
#define UNIQUE_H

#define PY_Suint64_t_CLEAN

#include <inttypes.h>
#include <string.h>
#include <Python.h>

#include "../hashmap/hashmap.h"
#include "../types.h"


PyObject *unique(PyObject *self, PyObject *args);

#endif
