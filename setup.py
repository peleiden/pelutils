import subprocess
from setuptools import setup, find_packages
from distutils.command.install import install as install_

with open("README.md") as readme_file:
    README = readme_file.read()

with open("HISTORY.md") as history_file:
    HISTORY = history_file.read()

# To update
# 1. Increment version below and document this in HISTORY.md (and possibly README.md)
# 2. Make master up to date with rebase
# 3. `rm -rf dist`
# 4. `python setup.py sdist bdist_wheel`
# 5. `twine upload dist/*`
# To install locally
# From root of repository, run
# `pip install ./ --upgrade`

class install(install_):
    def run(self):
        subprocess.call(["make", "clean"])
        subprocess.call(["make"])
        super().run()

setup_args = dict(
    name             = "pelutils",
    version          = "0.6.0",
    description      = "Utility functions that are often useful",
    long_description_content_type = "text/markdown",
    long_description = README + "\n\n" + HISTORY,
    license          = "BSD-3-Clause",
    packages         = find_packages(),
    package_data     = { "pelutils.ds": ["ds/ds.so"] },
    author           = "Søren Winkel Holm, Asger Laurits Schultz",
    author_email     = "swholm@protonmail.com",
    keywords         = [ "utility", "logger", "parser", "profiling"],
    url              = "https://github.com/peleiden/pelutils",
    download_url     = "https://pypi.org/project/pelutils/",
    install_requires = [ "numpy", "gitpython", "rich", "regex", "tqdm" ],
    extras_require   = { "ds": ["torch", "matplotlib", "scipy"] },
    cmdclass         = { "install": install },
)


if __name__ == "__main__":
    setup(**setup_args)
