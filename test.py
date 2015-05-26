# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import unittest, tempfile, shutil, os

import build # 3rd-party

class Test(unittest.TestCase):

	def test_make(self):
		# generate a Makefile, check it's detected and run
		dirname = tempfile.mkdtemp()
		with open(os.path.join(dirname, "Makefile"), "w") as f:
			f.write("all: ; touch %s/success" % dirname)
		build.main("-C", dirname, "compile")
		self.assertTrue(os.path.exists(os.path.join(dirname, "success")))
		shutil.rmtree(dirname)

if __name__ == "__main__": unittest.main(verbosity = 2)
