all: clean  build

build: swig
	python setup.py build
	cp build/lib.linux-i686-2.6/_pyalpmm_raw.so .

swig:
	swig -python pyalpmm_raw/pyalpmm_raw.i
	cp pyalpmm_raw/pyalpmm_raw.py .

unlockdb:
	$([[ -x /var/lib/pacman/db.lck [] && rm -rf /var/lib/pacman/db.lck)

pyclean:
	rm -rf build MANIFEST
	rm -f pyalpmm/*.pyc pyalpmm/*.py~
	rm -f *~ *.pyc *.so

swigclean:
	rm -f pyalpmm_raw/pyalpmm_raw_wrap.c
	rm -f pyalpmm_raw/pyalpmm_raw.py
	rm -f pyalpmm_raw.py

clean: pyclean swigclean

install:
	python setup.py install



