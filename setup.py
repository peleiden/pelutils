import os
import sys
from glob import glob as glob  # glob

from setuptools import find_packages, setup
from setuptools.extension import Extension

sys.path.append("pelutils")
from __version__ import __version__

requirements = [
    "numpy>=2.0",
    "gitpython>=3.1.0",
    "rich>=10.0.0",
    "py-cpuinfo>=8.0.0",
    "psutil>=5.8.0",
    "matplotlib>=3.3",
    "scipy>=1.6",
    "tqdm>=4.55",
    "pydantic>=2",
    "typing_extensions>=4.6",
]
requirements_dev = [
    "torch>=2",
    "pytest==8.4.2",
    "pytest-cov==7.0.0",
    "coveralls>=4.0.0",
    "coverage==7.10.7",
    "wheel",
    "setuptools>=60.0.0",
    "ruff==0.15.8",
    "basedpyright==1.39.0",
    "freezegun>=1.5",
    "ipdb",
]
requirements_docs = [
    "sphinx",
    "sphinx-autobuild",
    "furo",
    "myst-parser",
]

with open("README.md") as readme_file:
    README = readme_file.read()

c_files = list()
for root, __, files in os.walk("pelutils/_c"):
    c_files += [os.path.join(root, f) for f in files if f.endswith(".c")]

setup_args = dict(
    name="pelutils",
    version=__version__,
    description="The Swiss army knife of Python projects",
    long_description_content_type="text/markdown",
    long_description=README,
    license="MIT",
    packages=find_packages(exclude=("tests", "tests.*")),
    package_data={"pelutils": ["py.typed"]},
    author="Asger Laurits Schultz, Søren Winkel Holm",
    author_email="asger.s@protonmail.com, swholm@protonmail.com",
    keywords=["utility", "logger", "parser", "profiling", "plotting"],
    url="https://github.com/peleiden/pelutils",
    download_url="https://pypi.org/project/pelutils/",
    install_requires=requirements,
    extras_require={"docs": requirements_docs, "dev": requirements_dev + requirements_docs},
    entry_points={
        "console_scripts": [
            "linecounter = pelutils._entry_points.linecounter:run",
        ]
    },
    ext_modules=[
        Extension(
            name="_pelutils_c",
            sources=c_files,
            extra_compile_args=["-DMS_WIN64"] if sys.platform == "win32" else [],
        )
    ],
    license_files=[os.path.join("pelutils", "_c", "hashmap", "LICENSE")],
    python_requires=">=3.11",
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
)

if __name__ == "__main__":
    setup(**setup_args)
