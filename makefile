
SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.PHONY: all fresh dependencies install fulluninstall uninstall removedeps

all: dependencies

fresh: fulluninstall dependencies

fulluninstall: uninstall cleancode

install:
	ln -s -f $(ROOT_DIR)/bin/gitconsensus /usr/local/bin/gitconsensus

dependencies:
	if [ ! -d $(ROOT_DIR)/env ]; then virtualenv $(ROOT_DIR)/env; fi
	source $(ROOT_DIR)/env/bin/activate; yes w | pip install -r $(ROOT_DIR)/requirements.txt

uninstall:
	if [ -L /usr/local/bin/gitconsensus ]; then \
		rm /usr/local/bin/gitconsensus; \
	fi;

cleancode:
	rm -rf $(ROOT_DIR)/*.pyc
	# Remove existing environment
	if [ -d $(ROOT_DIR)/env ]; then \
		rm -rf $(ROOT_DIR)/env; \
	fi;
