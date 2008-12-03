from distutils.core import setup
from distutils.core import Extension
 
module = Extension("_pyalpmm_raw",
                   libraries=["alpm"],
                   sources=["pyalpmm_raw/pyalpmm_raw_wrap.c"])
                        
 
setup(name="pyalpmm",
      description="High-Level Python API for the Arch-Linux-Package-Manager library" ,
      version="0.1",
      author="Markus Meissner",
      author_email="markus@evigo.net",
      url="http://www.infolexikon.de",
      ext_modules=[module],
      packages=["pyalpmm"],
      py_modules=["pyalpmm_raw"])
