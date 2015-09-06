# REF: https://packaging.python.org

import setuptools

setuptools.setup(
	name = "buildstack", # https://www.python.org/dev/peps/pep-0426/#name
	version = "5.2.0", # https://www.python.org/dev/peps/pep-0440/
	packages = ["buildstack"], # https://pythonhosted.org/setuptools/setuptools.html#using-find-packages
	#description = "",
	#long_description = "",
	#url = "",
	author = "florent claerhout",
	author_email = "code@fclaerhout.fr",
	license = "MIT",
	#classifiers = [], # https://pypi.python.org/pypi?%3Aaction=list_classifiers
	#keyword = [],
	#py_modules = [],
	install_requires = [
		"pyutils >=5,<8a0",
		"docopt",
		"PyYAML",
	], # https://packaging.python.org/en/latest/requirements.html#install-requires-vs-requirements-files
	#package_data = {},
	#data_files = {},
	entry_points = {
		"console_scripts": [
			"buildstack=buildstack:main",
		],
	}, # https://pythonhosted.org/setuptools/setuptools.html#automatic-script-creation
	test_suite = "test",
	tests_require = [
		"pyutils >=5,<8a0",
		"docopt",
		"PyYAML",
	],
	#extra_require = {},
	#setup_requires = [],
	dependency_links = [
		"https://pypi.fclaerhout.fr/simple/pyutils",
	], # https://pythonhosted.org/setuptools/setuptools.html#dependencies-that-aren-t-in-pypi
)
