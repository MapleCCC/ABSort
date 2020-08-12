MAKEFLAGS += .silent

all:
	python -m absort sample.py

format:
	autopep8 --in-place --recursive --aggressive --aggressive --select E501 --max-line-length 88 .
	isort .
	black .

prof:
	kernprof -lv absort.py sample.py

type-check:
	mypy .
	pyright
	# TODO pytype, pyre-check

lint:
	find . -type f -name "*.py" | xargs pylint

unused-imports:
	find . -type f -name "*.py" | xargs pylint --disable=all --enable=W0611

todo:
	rg "# TODO|# FIXME" --glob !Makefile

clean:
	rm -rf __pycache__/

.PHONY: all format prof type-check lint unused-imports todo clean
