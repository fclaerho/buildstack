# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

import unittest, shutil, sys, os

import build, utils # 3rd-party

FOOBUILD = """
for i
do
	touch foo.$i
done
"""

def _foo_on_flush(profileid, filename, targets):
	args = map(lambda target: target.name, targets)
	del targets[:]
	yield ["bash", filename] + args

# register manifest for a pretend stack "foo"
build.buildstack.manifests.append({
	"name": "foo",
	"filenames": ["Foobuild"],
	"on_flush": _foo_on_flush,
})

class CoreTest(unittest.TestCase):

	def setUp(self):
		# generate build manifest
		self.dirname = utils.mkdir()
		with open(os.path.join(self.dirname, "Foobuild"), "w") as fp:
			fp.write(FOOBUILD)

	def tearDown(self):
		shutil.rmtree(self.dirname)

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
		build.main("-C", self.dirname, "clean")

	def test_compile(self):
		build.main("-C", self.dirname, "compile")
		self.assert_is_compiled()

	def test_test(self):
		build.main("-C", self.dirname, "test")
		self.assert_is_tested()

	def test_package(self):
		build.main("-C", self.dirname, "package")
		self.assert_is_packaged()

	def test_install(self):
		build.main("-C", self.dirname, "install")
		self.assert_is_installed()

	def test_publish(self):
		build.main("-C", self.dirname, "publish")
		self.assert_is_published()

	def test_build(self):
		build.main("-C", self.dirname, "clean", "compile", "test", "package", "install", "publish")
		self.assert_is_cleaned()
		self.assert_is_compiled()
		self.assert_is_tested()
		self.assert_is_packaged()
		self.assert_is_installed()
		self.assert_is_published()

# experimental
if False:
	class StackTest(object):

		git_url = None
		target_paths = []

		def setUp(self):
			self.dirname = utils.mkdir()
			basename = os.path.basename(self.git_url)
			rootname, extname = os.path.splitext(basename)
			self.path = os.path.join(self.dirname, rootname)
			utils.check_call("git", "-C", self.dirname, "clone", self.git_url)

		def tearDown(self):
			utils.remove(self.dirname)

		def test_clean_compile(self):
			build.main("-C", self.path, "clean", "compile")
			for path in self.target_paths:
				self.assertTrue(os.path.exists(os.path.join(self.path, path)))

	#
	# list of C projects on github:
	# https://api.github.com/legacy/repos/search/C?language=C
	#

	class PTest(StackTest, unittest.TestCase):
		git_url = "https://github.com/orangeduck/ptest"
		target_paths = ["example", "example2"]

	class SnappyC(StackTest, unittest.TestCase):

		git_url = "https://github.com/andikleen/snappy-c"
		target_paths = ["scmd", "sgverify", "verify"]

	class GeoIPAPI(StackTest, unittest.TestCase):
		git_url = "https://github.com/maxmind/geoip-api-c"
		target_paths = ["apps/geoiplookup", "apps/geoiplookup6"]

	@unittest.skip("automake fails due to missing macro -- issue reported")
	class ASN1C(StackTest, unittest.TestCase):
		git_url = "https://github.com/vlm/asn1c"
		target_paths = []

if __name__ == "__main__": unittest.main(verbosity = 2)
