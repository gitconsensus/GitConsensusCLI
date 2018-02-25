
SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.PHONY: all fresh dependencies install fulluninstall uninstall removedeps

all: dependencies

clean:
	rm -rf $(ROOT_DIR)/gitconsensus/*.pyc
	rm -rf $(ROOT_DIR)/env
	rm -rf $(ROOT_DIR)/dist
	rm -rf $(ROOT_DIR)/build
	rm -rf $(ROOT_DIR)/*.egg-info

dependencies:
	if [ ! -d $(ROOT_DIR)/env ]; then python3 -m venv $(ROOT_DIR)/env; fi
	source $(ROOT_DIR)/env/bin/activate; yes w | python -m pip install -e .[dev]

package:
	source $(ROOT_DIR)/env/bin/activate; python setup.py bdist_wheel
