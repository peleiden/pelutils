import subprocess
from setuptools import setup, find_packages
from distutils.command.install import install as install_


with open("README.md") as readme_file:
    README = readme_file.read()

with open("HISTORY.md") as history_file:
    HISTORY = history_file.read()

class install(install_):
    def run(self):
        subprocess.call("git submodule update --init --recursive".split())
        subprocess.call("make clean".split())
        subprocess.call("make".split())
        super().run()

setup_args = dict(
    name             = "pelutils",
    version          = "0.6.7",
    description      = "Utility functions that are often useful",
    long_description_content_type = "text/markdown",
    long_description = README + "\n\n" + HISTORY,
    license          = "BSD-3-Clause",
    packages         = find_packages(),
    package_data     = { "pelutils.ds": ["ds/ds.so"] },
    author           = "Søren Winkel Holm, Asger Laurits Schultz",
    author_email     = "swholm@protonmail.com",
    keywords         = [ "utility", "logger", "parser", "profiling" ],
    url              = "https://github.com/peleiden/pelutils",
    download_url     = "https://pypi.org/project/pelutils/",
    install_requires = [ "numpy>=1.18.0", "gitpython>=3.1.0", "rich>=10.0.0", "click>=7.0.0" ],
    extras_require   = { "ds": ["torch>=1.7.0", "matplotlib>=3.1.0", "scipy>=1.4.1", "tqdm>=4.0.0"] },
    entry_points     = { "console_scripts": ["linecounter = pelutils.ds._linecounter:linecounter"] },
    cmdclass         = { "install": install },
)

if __name__ == "__main__":
    setup(**setup_args)
