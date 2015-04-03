# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import setuptools

setuptools.setup(
	name = "bs",
	author = "fclaerhout.fr",
	version = "1.0.1",
	license = "MIT",
	test_suite = "test",
	py_modules = ["bs"],
	description = "build stack helper",
	author_email = "contact@fclaerhout.fr",
	entry_points = {"console_scripts": ["bs=bs:main"]},
	tests_require = ["docopt"],
	install_requires = ["docopt"],
)
