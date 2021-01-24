CC=gcc
CFLAGS=-fPIC -Wall -O3
LDFLAGS=-shared

all: pelutils/ds/ds.so

pelutils/ds/ds.o: pelutils/ds/ds.c

pelutils/ds/ds.so: pelutils/ds/ds.o
	$(CC) pelutils/ds/ds.o pelutils/ds/hashmap.c/hashmap.c -shared -fPIC -o pelutils/ds/ds.so
	$(RM) pelutils/ds/*.o

clean:
	$(RM) pelutils/ds/*.o pelutils/ds/*.so
