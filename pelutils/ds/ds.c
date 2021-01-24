#include <string.h>
#include "hashmap.c/hashmap.h"

// Contains a pointer to an array element and a reference to the stride
struct elem {
    void* p_elem;
    size_t* p_stride;
};

typedef struct hashmap hashmap;

uint64_t hash(const void* elem, uint64_t seed0, uint64_t seed1) {
    const struct elem* e = elem;
    return hashmap_sip(e->p_elem, *e->p_stride, seed0, seed1);
}

int compare(const void* elem1, const void* elem2, void* udata) {
    // Compares two array elements
    const struct elem* e1 = elem1;
    const struct elem* e2 = elem2;
    return memcmp(e1->p_elem, e2->p_elem, *e1->p_stride);
}

long unique(size_t n,  // Number of array elements
            size_t stride,       // Number of bytes between elements on primary axis
            void* array,      // Non-empty, contiguous array of any shape
            long* index,      // Array of size n to put unique values
            long* inverse,    // Array of size n to put inverse values
            long* counts      // Array of size n to put number of each unique element
) {
    hashmap* map = hashmap_new(sizeof(void*), 0, 0, 0, hash, compare, NULL);
    size_t n_unique = 0;
    for (size_t i = 0; i < n; i ++) {
        // Construct element
        struct elem this_elem = {
            .p_elem = array + stride * i,
            .p_stride = &stride,
        };
        // Check if already in map
        struct elem* p_found_elem = hashmap_get(map, &this_elem);
        if (p_found_elem != NULL) {
            // Get index of found element by difference in memory address
            size_t found_index = (p_found_elem->p_elem - array) / stride;
            if (inverse != NULL)
                inverse[i] = inverse[found_index];
            if (counts != NULL)
                counts[found_index] ++;
        } else {
            // Set new element in hashmap
            hashmap_set(map, &this_elem);
            if (index != NULL)
                index[n_unique] = i;
            if (inverse != NULL)
                inverse[i] = n_unique;
            if (counts != NULL)
                counts[i] = 1;
            n_unique ++;
        }
    }
    hashmap_free(map);
    return n_unique;
}

