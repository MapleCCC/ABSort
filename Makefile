MAKEFLAGS += .silent

all:
	python -m absort sample.py

test:
	pytest tests

stress-test:
	time absort --quiet "D:/Program Files/Python38/Lib/site-packages"

format:
	autopep8 --in-place --recursive --aggressive --aggressive --select E501 --max-line-length 88 .
	isort .
	black .

prof:
	# kernprof -lv absort/__main__.py sample.py
	scripts/profile.py

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

.PHONY: all test stress-test format prof type-check lint unused-imports todo clean
