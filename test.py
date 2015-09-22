# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

import unittest, sys, os

import buildstack, fckit # 3rd-party

################
# CORE TESTING #
################

#
# Dummy build stack "foo".
# The build tool create a file for any called target.
#

FOOBUILD = """
for i
do
	touch foo.$i
done
"""

def _foo_on_flush(filename, targets):
	args = map(lambda target: target.name, targets)
	del targets[:]
	yield ["bash", filename] + args

MANIFEST = {
	"name": "foo",
	"filenames": ["Foobuild"],
	"on_flush": _foo_on_flush,
}

class CoreTest(unittest.TestCase):

	def setUp(self):
		# generate build manifest
		self.dirname = fckit.mkdir()
		with open(os.path.join(self.dirname, "Foobuild"), "w") as fp:
			fp.write(FOOBUILD)
		self.buildstack = buildstack.BuildStack(
			manifests = (MANIFEST,),
			path = self.dirname)

	def tearDown(self):
		fckit.remove(self.dirname)

	def assert_is_cleaned(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.clean")))

	def assert_is_compiled(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.compile")))

	def assert_is_tested(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.test")))

	def assert_is_installed(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.install")))

	def assert_is_packaged(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.package")))

	def assert_is_published(self):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.publish")))

	def test_clean(self):
		self.buildstack.clean()
		self.buildstack.flush()

	def test_compile(self):
		self.buildstack.compile()
		self.buildstack.flush()
		self.assert_is_compiled()

	def test_test(self):
		self.buildstack.test()
		self.buildstack.flush()
		self.assert_is_compiled()
		self.assert_is_tested()

	def test_package(self):
		self.buildstack.package()
		self.buildstack.flush()
		self.assert_is_compiled()
		self.assert_is_tested()
		self.assert_is_packaged()

	def test_install(self):
		self.buildstack.install()
		self.buildstack.flush()
		self.assert_is_compiled()
		self.assert_is_tested()
		self.assert_is_packaged()
		self.assert_is_installed()

	def test_publish(self):
		self.buildstack.publish()
		self.buildstack.flush()
		self.assert_is_compiled()
		self.assert_is_tested()
		self.assert_is_packaged()
		self.assert_is_published()

class VersionTest(unittest.TestCase):

	def setUp(self):
		self.version = buildstack.Version(1, 2, 3)

	def test_bump_major(self):
		self.assertEqual(self.version.bump("major").number, buildstack.Version(2, 0, 0).number)

	def test_bump_minor(self):
		self.assertEqual(self.version.bump("minor").number, buildstack.Version(1, 3, 0).number)

	def test_bump_patch(self):
		self.assertEqual(self.version.bump("patch").number, buildstack.Version(1, 2, 4).number)

	def test_bump_N(self):
		self.assertEqual(self.version.bump(3).number, buildstack.Version(1, 2, 3, 1).number)

if __name__ == "__main__": unittest.main(verbosity = 2)
