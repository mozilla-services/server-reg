APPNAME = server-reg
DEPS = server-core
VIRTUALENV = virtualenv
NOSE = bin/nosetests -s --with-xunit
TESTS = syncreg/tests
PYTHON = bin/python
EZ = bin/easy_install
COVEROPTS = --cover-html --cover-html-dir=html --with-coverage --cover-package=keyexchange
COVERAGE = bin/coverage
PYLINT = bin/pylint
PKGS = syncreg
PYPI2RPM = bin/pypi2rpm.py
BUILDAPP = bin/buildapp


.PHONY: all build test build_rpms mach

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(EZ) -U MoPyTools
	$(BUILDAPP) $(APPNAME) $(DEPS)
	$(EZ) nose
	$(EZ) WebTest
	$(EZ) Funkload
	$(EZ) pylint
	$(EZ) coverage
	$(EZ) pypi2rpm
	$(EZ) wsgi_intercept
	$(EZ) wsgiproxy

test:
	$(NOSE) $(TESTS)

build_rpms:
	rm -rf $(CURDIR)/rpms
	mkdir $(CURDIR)/rpms
	rm -rf build; $(PYTHON) setup.py --command-packages=pypi2rpm.command bdist_rpm2 --spec-file=SyncReg.spec --dist-dir=$(CURDIR)/rpms --binary-only
	cd deps/server-core; rm -rf build; ../../$(PYTHON) setup.py --command-packages=pypi2rpm.command bdist_rpm2 --spec-file=Services.spec --dist-dir=$(CURDIR)/rpms --binary-only
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms cef --version=0.2
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms webob --version=1.0.7
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms paste --version=1.7.5.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms pastedeploy --version=1.3.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms pastescript --version=1.7.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms mako --version=0.4.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms markupsafe --version=0.12
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms beaker --version=1.5.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms python-memcached --version=1.47
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms simplejson --version=2.1.6
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms routes --version=1.12.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms sqlalchemy --version=0.6.6
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms mysql-python --version=1.2.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms wsgiproxy --version=0.2.2
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms recaptcha-client --version=1.0.6

mach: build build_rpms
	mach clean
	mach yum install python26 python26-setuptools
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/gunicorn-0.11.2-1moz.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla/nginx-0.7.65-4.x86_64.rpm
	mach yum install rpms/*
	mach chroot python2.6 -m syncreg.run
