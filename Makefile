all: clean  build

DESTDIR=/
RELEASE=0.2.1.1
PKGREL=1

ARCH=`uname -m`



build: swig
	python setup.py build
	cp build/lib.linux-$(ARCH)-2.7/_pyalpmm_raw.so .

swig:
	swig -python -copyctor -Wall pyalpmm_raw/pyalpmm_raw.i
	cp pyalpmm_raw/pyalpmm_raw.py .

clean:
	rm -rf build MANIFEST pyalpmm-*.pkg.tar.gz
	rm -f pyalpmm/*.py{c,~}
	rm -f *{~,pyc,so}
	rm -f pyalpmm_raw{.py,/pyalpmm_raw_wrap.c,/pyalpmm_raw.py}
	rm -rf arch/{release,svn}/{pyalpmm*,src,pkg}

install:
	python setup.py install --root $(DESTDIR)

create_tag:
	svn copy svn://infolexikon.de/pyalpmm/trunk \
		 svn://infolexikon.de/pyalpmm/tags/pyalpmm-$(RELEASE) \
		 -m "Tagging the $(RELEASE)"

arch_release: clean
	cd arch/release/ && makepkg && cp pyalpmm-$(RELEASE)-$(PKGREL).pkg.tar.gz ../../
	# Package placed in ./ please install with pacman -U

arch_svn: clean
	cd arch/svn && makepkg && cp pyalpmm-svn-*.pkg.tar.gz ../../
	# Package placed in ./ please install with pacman -U
