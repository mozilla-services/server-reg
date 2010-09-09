VIRTUALENV = virtualenv
BIN = bin

.PHONY: all build check coverage test mysqltest redisqltest doc alltest

all:	build test

build:
	$(VIRTUALENV) --no-site-packages .
	$(BIN)/easy_install nose
	$(BIN)/easy_install coverage
	$(BIN)/easy_install flake8
	$(BIN)/python setup.py develop

check:
	rm -rf syncreg/templates/*.py
	$(BIN)/flake8 syncreg

coverage:
	$(BIN)/nosetests -s --cover-html --cover-html-dir=html --with-coverage --cover-package=syncreg syncreg
	WEAVE_TESTFILE=mysql $(BIN)/nosetests -s --cover-html --cover-html-dir=html --with-coverage --cover-package=syncreg syncreg 

test:
	$(BIN)/nosetests -s syncreg

mysqltest:
	WEAVE_TESTFILE=mysql $(BIN)/nosetests -s syncreg

redisqltest:
	WEAVE_TESTFILE=redisql $(BIN)/nosetests -s syncreg

ldaptest:
	WEAVE_TESTFILE=ldap $(BIN)/nosetests -s syncreg


alltest: test mysqltest redisqltest ldaptest

doc:
	$(BIN)/sphinx-build doc/source/ doc/build/

