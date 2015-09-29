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

def _foo_on_get(filename, targets, requirementid):
	yield "bash", filename, "get"

def _foo_on_flush(filename, targets):
	args = map(lambda target: target.name, targets)
	del targets[:]
	yield ["bash", filename] + args

MANIFEST = {
	"name": "foo",
	"filenames": ["Foobuild"],
	"on_get": _foo_on_get,
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

	def assert_done(self, name):
		self.assertTrue(os.path.exists(os.path.join(self.dirname, "foo.%s" % name)))

	def test_get_lifecycle(self):
		self.buildstack.get()
		self.buildstack.flush()
		self.assert_done("get")

	def test_clean_lifecycle(self):
		self.buildstack.clean()
		self.buildstack.flush()
		self.assert_done("clean")

	def test_test_lifecycle(self):
		self.buildstack.test()
		self.buildstack.flush()
		self.assert_done("compile")
		self.assert_done("test")

	def test_run_lifecycle(self):
		self.buildstack.run()
		self.buildstack.flush()
		self.assert_done("compile")
		self.assert_done("run")

	def test_package_lifecycle(self):
		self.buildstack.package()
		self.buildstack.flush()
		self.assert_done("compile")
		self.assert_done("test")
		self.assert_done("package")

	def test_publish_lifecycle(self):
		self.buildstack.publish()
		self.buildstack.flush()
		self.assert_done("compile")
		self.assert_done("test")
		self.assert_done("package")
		self.assert_done("publish")

	def test_uninstall_lifecycle(self):
		self.buildstack.uninstall()
		self.buildstack.flush()
		self.assert_done("uninstall")

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
