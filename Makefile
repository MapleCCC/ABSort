MAKEFLAGS += .silent

all:
	./absort.py sample.py

format:
	autopep8 --in-place --recursive --aggressive --aggressive --select E501 --max-line-length 88 .
	isort .
	black .

prof:
	kernprof -lv absort.py sample.py

clean:

.PHONY: all format prof clean
