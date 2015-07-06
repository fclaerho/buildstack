# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import setuptools

setuptools.setup(
	name = "build",
	author = "fclaerhout.fr",
	version = "2.7.3",
	license = "MIT",
	packages = ["buildstack"],
	test_suite = "test",
	py_modules = ["build"],
	description = "build stack wrapper",
	author_email = "contact@fclaerhout.fr",
	entry_points = {"console_scripts": ["build=build:main"]},
	tests_require = ["pyutils", "docopt"],
	install_requires = ["pyutils", "docopt"],
	# Note to self: as pyutils uses build to publish itself, we pull from git instead of pypi.
	dependency_links = ["git+https://github.com/fclaerho/pyutils.git@v1.2.2#egg=pyutils-1.2.2"],
)
