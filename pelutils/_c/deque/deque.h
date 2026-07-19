#ifndef DEQUE_H
#define DEQUE_H

#include <stdlib.h>

#include "../types.h"


struct deque_node_t {
    struct deque_node_t *prev_node;
    struct deque_node_t *next_node;
    i64 value;
};
typedef struct deque_node_t deque_node_t;

struct deque_t {
    u64 num_elems;
    deque_node_t *first_node;
    deque_node_t *last_node;
};
typedef struct deque_t deque_t;

/* Initialise a double-ended queue. */
deque_t *deque_init();

/* Pop the left-most element. Return if an item was popped. */
bool deque_pop_left(deque_t *deque, i64 *value);

/* Append an item to the right of a double-ended queue. */
void deque_append_right(deque_t *deque, i64 value);

/* Free a double-ended queue. */
void deque_free(deque_t *deque);

#endif
