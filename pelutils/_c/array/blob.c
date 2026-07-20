#include "blob.h"

static u64 hash(const void *elem, u64 seed0, u64 seed1) {
    node_t *entry = elem;
    return hashmap_murmur(entry->grid_coord_p, entry->ndim * sizeof(*entry->grid_coord_p), seed0, seed1);
}
static int compare(const void *elem1, const void *elem2, void *udata) {
    node_t *entry1 = elem1;
    node_t *entry2 = elem2;
    return memcmp(entry1->grid_coord_p, entry2->grid_coord_p, entry1->ndim * sizeof(*entry1->grid_coord_p));
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

    if (!PyArg_ParseTuple(args, "LLLLL", &pointers, &wrap_axis_sizes, &index_array, &num_indices, &ndim))
        return NULL;


    hashmap *coord_to_index = hashmap_new(sizeof(node_t), 0, 0, 0, hash, compare, NULL, NULL);
    pointers[0] = coord_to_index;

    for (u64 i = 0; i < num_indices; ++ i) {
        node_t node = { .grid_coord_p = index_array + i * ndim, .index = i, .ndim = ndim };
        cond_wrap(node.grid_coord_p, wrap_axis_sizes, ndim);
        hashmap_set(coord_to_index, &node);
    }

    Py_RETURN_NONE;
}

PyObject *free_lookup_table(PyObject *self, PyObject *args) {
    void **pointers;

    if (!PyArg_ParseTuple(args, "L", &pointers))
        return NULL;

    hashmap *map = (hashmap *)pointers[0];
    hashmap_free(map);

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
    if (!PyArg_ParseTuple(args, "LLLLLLO!", &pointers, &wrap_axis_sizes, &index_array, &start_index, &num_indices, &ndim, &PyList_Type, &blob_indices_list))
        return NULL;

    hashmap *coord_to_index = pointers[0];

    // Do BFS from the given starting row
    deque_t *q = deque_init();
    deque_append_right(q, start_index);
    node_t init_node = { .grid_coord_p = index_array + ndim * start_index, .ndim = ndim };
    cond_wrap(init_node.grid_coord_p, wrap_axis_sizes, ndim);
    hashmap_delete(coord_to_index, &init_node);

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
                node_t neighbour = { .grid_coord_p = neighbour_coord, .ndim = ndim };
                cond_wrap(neighbour.grid_coord_p, wrap_axis_sizes, ndim);
                node_t *found_node = hashmap_delete(coord_to_index, &neighbour);
                if (found_node != NULL) {
                    // Neighbour exists, so add it to the queue
                    deque_append_right(q, found_node->index);
                }
            }
        }
    }

    free(neighbour_coord);
    deque_free(q);

    Py_RETURN_NONE;
}
