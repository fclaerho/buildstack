# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import setuptools

setuptools.setup(
	name = "code",
	author = "fclaerhout.fr",
	version = "1.0.0rc2",
	license = "MIT",
	test_suite = "test",
	description = "build stack helper",
	author_email = "contact@fclaerhout.fr",
	entry_points = {"console_scripts": ["code=main:main"]},
	install_requires = ["docopt"],
)
