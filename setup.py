# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import setuptools

setuptools.setup(
	name = "build",
	author = "fclaerhout.fr",
	version = "1.3.1",
	license = "MIT",
	packages = ["buildstack"],
	test_suite = "test",
	py_modules = ["build"],
	description = "build stack wrapper",
	author_email = "contact@fclaerhout.fr",
	entry_points = {"console_scripts": ["build=build:main"]},
	tests_require = ["docopt"],
	install_requires = ["docopt"],
)
