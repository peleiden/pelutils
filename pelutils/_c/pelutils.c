#include "ds.h"


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
    // Needed for numpy arrays. See
    // https://stackoverflow.com/questions/37943699/crash-when-calling-pyarg-parsetuple-on-a-numpy-array
    PyObject* module = PyModule_Create(&_pelutils_c_module);
    import_array();
    return module;
}
