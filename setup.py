# REF: https://packaging.python.org

import setuptools

setuptools.setup(
	name = "build", # https://www.python.org/dev/peps/pep-0426/#name
	version = "2.8.1", # https://www.python.org/dev/peps/pep-0440/
	packages = ["buildstack"], # https://pythonhosted.org/setuptools/setuptools.html#using-find-packages
	#description = "",
	#long_description = "",
	#url = "",
	#author = "",
	author_email = "contact@fclaerhout.fr",
	#license = "",
	#classifiers = [], # https://pypi.python.org/pypi?%3Aaction=list_classifiers
	#keyword = [],
	py_modules = ["build"],
	install_requires = ["pyutils", "docopt"], # https://packaging.python.org/en/latest/requirements.html#install-requires-vs-requirements-files
	#package_data = {},
	#data_files = {},
	entry_points = {
		"console_scripts": [
			"build=build:main",
		],
	}, # https://pythonhosted.org/setuptools/setuptools.html#automatic-script-creation
	test_suite = "test",
	tests_require = ["pyutils", "docopt"],
	#extra_require = {},
	#setup_requires = [],
	dependency_links = [
		"https://pypi.fclaerhout.fr/simple/pyutils",
		"git+https://github.com/fclaerho/pyutils/tarball/master@v1.2.2#egg=pyutils-1.2.2",
	], # https://pythonhosted.org/setuptools/setuptools.html#dependencies-that-aren-t-in-pypi
)
