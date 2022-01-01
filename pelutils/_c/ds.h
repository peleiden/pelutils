#ifndef DS_H
#define DS_H
#include <Python.h>
#include "hashmap.c/hashmap.h"

/* Prototypes of all functions exposed by the c module */

/*
size_t n,       // Number of array elements
size_t stride,  // Number of bytes between elements on primary axis
void* array,    // Non-empty, contiguous array of any shape
long* index,    // Array of size n to put unique values
long* inverse,  // Array of size n to put inverse values
long* counts    // Array of size n to put number of each unique element
*/
static PyObject* unique(PyObject* self, PyObject* args);
#endif
