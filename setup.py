import os
import sys

from setuptools import setup
from setuptools.extension import Extension

c_files = [os.path.join(root, filename) for root, _, files in os.walk("pelutils/_c") for filename in files if filename.endswith(".c")]

setup(
    ext_modules=[
        Extension(
            name="_pelutils_c",
            sources=c_files,
            extra_compile_args=["-DMS_WIN64"] if sys.platform == "win32" else [],
        )
    ]
)
