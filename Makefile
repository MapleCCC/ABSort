MAKEFLAGS += .silent

all:
	./absort.py sample.py

prof:
	kernprof -lv absort.py sample.py

clean:

.PHONY: all prof clean
