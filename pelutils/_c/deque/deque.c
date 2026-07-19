#include "deque.h"

deque_t *deque_init() {
    deque_t *deque = malloc(sizeof(deque_t));
    deque->num_elems = 0;
    deque->first_node = NULL;
    deque->last_node = NULL;
    return deque;
}

bool deque_pop_left(deque_t *deque, i64 *value) {
    if (deque->num_elems == 0) {
        return false;
    }
    deque_node_t *node = deque->first_node;
    if (value != NULL) {
        *value = node->value;
    }

    if (deque->num_elems == 1) {
        deque->first_node = NULL;
        deque->last_node = NULL;
    } else {
        deque->first_node = node->next_node;
    }

    free(node);
    deque->num_elems --;
}

void deque_append_right(deque_t *deque, i64 value) {
    deque_node_t *node = malloc(sizeof(deque_node_t));
    node->next_node = NULL;
    node->value = value;

    if (deque->num_elems == 0) {
        node->prev_node = NULL;
        deque->first_node = node;
    } else {
        deque->last_node->next_node = node;
    }

    deque->last_node = node;
    deque->num_elems ++;
}

void deque_free(deque_t *deque) {
    while (deque->num_elems > 0) {
        deque_pop_left(deque, NULL);
    }
    free(deque);
}
