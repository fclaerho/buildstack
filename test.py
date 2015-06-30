# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

import tempfile, unittest, shutil, sys, os

import build # 3rd-party

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

class Test(unittest.TestCase):

	def setUp(self):
		# generate build manifest
		self.dirname = tempfile.mkdtemp()
		with open(os.path.join(self.dirname, "Foobuild"), "w") as fp:
			fp.write(FOOBUILD)

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
		self.assert_is_compiled()
		self.assert_is_tested()
		self.assert_is_packaged()
		self.assert_is_installed()
		self.assert_is_published()

	def tearDown(self):
		shutil.rmtree(self.dirname)

if __name__ == "__main__": unittest.main(verbosity = 2)
