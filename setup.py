from setuptools import setup, find_packages

with open('README.md') as readme_file:
	README = readme_file.read()

with open('HISTORY.md') as history_file:
	HISTORY = history_file.read()

# To update
# 1. Increment version below and document this in HISTORY.md (and possibly README.md)
# 2. Make master up to date with rebase
# 3. `rm -rf dist`
# 4. `python setup.py sdist bdist_wheel`
# 5. `twine upload dist/*`

setup_args = dict(
	name                          = 'pelutils',
	version                       = '0.1.2',
	description                   = 'Utility functions that are commmonly useful',
	long_description_content_type = "text/markdown",
	long_description              = README + '\n\n' + HISTORY,
	license                       = 'GPL-v2',
	packages                      = find_packages(),
	author                        = 'Søren Winkel Holm, Asger Laurits Schultz',
	author_email                  = 'swholm@protonmail.com',
	keywords                      = ['utility', 'logger', 'parser', 'profiling'],
	url                           = 'https://github.com/peleiden/pelutils',
	download_url                  = 'https://pypi.org/project/pelutils/'
)

install_requires = [
	'numpy',
	'torch',
]

if __name__ == '__main__':
	setup(**setup_args, install_requires=install_requires)
