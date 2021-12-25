CC=gcc
CFLAGS=-fPIC -Wall -O3
LDFLAGS=-shared

all: pelutils/so/ds.so

pelutils/so/ds.o:
	mkdir -p pelutils/so
	$(CC) pelutils/ds/ds.c $(CFLAGS) $(LDFLAGS) -o pelutils/so/ds.o

pelutils/so/ds.so: pelutils/so/ds.o
	mkdir -p pelutils/so
	$(CC) pelutils/so/ds.o pelutils/ds/hashmap.c/hashmap.c -shared -fPIC -o pelutils/so/ds.so
	$(RM) pelutils/so/*.o

clean:
	$(RM) pelutils/so/*.o pelutils/so/*.so
