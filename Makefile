MAKEFLAGS += .silent

SRC_DIR=absort
TEST_DIR=tests

all:
	python -m ${SRC_DIR} sample.py

pypy:
	pypy3 -m ${SRC_DIR} sample3.py

test:
	pytest ${TEST_DIR} --hypothesis-show-statistics

test-cov:
	pytest --cov=${SRC_DIR} ${TEST_DIR}
	# Alternatively, we can run: coverage run
	coverage html
	# TODO open in Chrome browser
	# python -m webbrowser -n htmlcov/index.html

stress-test:
	cd "D:/Program Files/Python39/Lib/site-packages" && time absort --check .
	# time python -m ${SRC_DIR} --check "D:\Program Files\Python39\Lib\site-packages\isort\main.py"

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

.PHONY: all pypy test test-cov stress-test format prof type-check lint unused-imports todo clean
