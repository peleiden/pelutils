#include <Python.h>

#include "array/unique.h"


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
