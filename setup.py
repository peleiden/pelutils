from distutils.command.build import build as build_
from distutils.core import Extension
from setuptools import setup, find_packages
from setuptools.extension import Extension
from shutil import rmtree
import subprocess

with open("requirements.txt") as requirements_file:
    requirements = requirements_file.read().splitlines()

with open("ds-requirements.txt") as ds_requirements_file:
    ds_requirements = ds_requirements_file.read().splitlines()

with open("dev-requirements.txt") as dev_requirements_file:
    dev_requirements = dev_requirements_file.read().splitlines()

with open("README.md") as readme_file:
    README = readme_file.read()

with open("CHANGELOG.md") as history_file:
    CHANGELOG = history_file.read()

class build(build_):

    def run(self):
        # Clear old builds to prevent older versions being used
        rmtree("build", ignore_errors=True)
        rmtree("dist", ignore_errors=True)
        # Clone all submodules
        subprocess.call("git submodule update --init --recursive".split())
        super().run()

setup_args = dict(
    name             = "pelutils",
    version          = "0.6.9",
    description      = "Utility functions that are often useful",
    long_description_content_type = "text/markdown",
    long_description = README + "\n\n" + CHANGELOG,
    license          = "BSD-3-Clause",
    packages         = find_packages(),
    package_data     = { "pelutils": [ "ds/ds.c", "ds/hashmap.c/*" ] },
    author           = "Asger Laurits Schultz, Søren Winkel Holm",
    author_email     = "asger.s@protonmail.com;swholm@protonmail.com",
    keywords         = [ "utility", "logger", "parser", "profiling" ],
    url              = "https://github.com/peleiden/pelutils",
    download_url     = "https://pypi.org/project/pelutils/",
    install_requires = [ requirements ],
    extras_require   = { "ds": ds_requirements, "tests": ds_requirements+dev_requirements },
    entry_points     = { "console_scripts": [
        "linecounter = pelutils.ds._linecounter:linecounter",
        "pelexamples = examples.cli:run",
    ] },
    cmdclass         = { "build": build },
    ext_modules      = [
        Extension(
            "ds_c",
            sources=["pelutils/ds/ds.c", "pelutils/ds/hashmap.c/hashmap.c"],
            extra_compile_args=["-DMS_WIN64"],
        )
    ],
    python_requires  = ">=3.7",
)

if __name__ == "__main__":
    setup(**setup_args)
