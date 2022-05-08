import os
import sys
from distutils.command.build import build as build_
from distutils.core import Extension
from glob import glob as glob  # glob
from setuptools import setup, find_packages
from setuptools.extension import Extension

sys.path.append("pelutils")
from __version__ import __version__

requirements = [
    "numpy>=1.17.0",
    "gitpython>=3.1.0",
    "rich>=10.0.0",
    "click>=7.0.0",
    "python-rapidjson>=1.5",
]
requirements_ds = [
    "torch>=1.7.0",
    "matplotlib>=3.1.0",
    "scipy>=1.4.1",
    "tqdm>=4.0.0",
]
requirements_dev = [
    "pytest>=6.2.4",
    "pytest-cov>=2.12.1",
    "coveralls>=3.2.0",
    "coverage>=5.5",
    "wheel",
    "setuptools>=60.0.0"
]

with open("README.md") as readme_file:
    README = readme_file.read()

c_files = list()
for root, __, files in os.walk("pelutils/_c"):
    c_files += [os.path.join(root, f) for f in files if f.endswith(".c")]

class CExtension(Extension):
    """ See this thread for details: https://stackoverflow.com/a/34830639/13196863 """

class build(build_):

    def build_extension(self, ext):
        self._ctypes = isinstance(ext, CExtension)
        return super().build_extension(ext)

    def get_export_symbols(self, ext):
        if self._ctypes:
            return ext.export_symbols
        return super().get_export_symbols(ext)

    def get_ext_filename(self, ext_name):
        if self._ctypes:
            return ext_name + '.so'
        return super().get_ext_filename(ext_name)

setup_args = dict(
    name             = "pelutils",
    version          = __version__,
    description      = "Utility functions that are often useful",
    long_description_content_type = "text/markdown",
    long_description = README,
    license          = "BSD-3-Clause",
    packages         = find_packages(),
    author           = "Asger Laurits Schultz, Søren Winkel Holm",
    author_email     = "asger.s@protonmail.com, swholm@protonmail.com",
    keywords         = [ "utility", "logger", "parser", "profiling", "plotting" ],
    url              = "https://github.com/peleiden/pelutils",
    download_url     = "https://pypi.org/project/pelutils/",
    install_requires = [ requirements ],
    extras_require   = { "ds": requirements_ds, "tests": requirements_ds+requirements_dev },
    entry_points     = { "console_scripts": [
        "linecounter = pelutils._entry_points.linecounter:linecounter",
        "pelexamples = examples.cli:run",
    ] },
    cmdclass         = { "build": build },
    ext_modules      = [
        CExtension(
            name               = "_pelutils_c",
            sources            = c_files,
            extra_compile_args = ["-DMS_WIN64"],
        )
    ],
    license_files    = [ os.path.join("pelutils", "_c", "hashmap.c", "LICENSE") ],
    python_requires  = ">=3.7",
)

if __name__ == "__main__":
    setup(**setup_args)
