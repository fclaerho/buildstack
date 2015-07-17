# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

"""
Environment variables:
  * TESTSTACKS: if set, build real-world code, otherwise test model only
  * FAILFAST
  * PAUSE: pause before cleaning the working directory, for inspection
"""

import unittest, shutil, sys, os

import build, utils # 3rd-party

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

def _foo_on_flush(profileid, filename, targets):
	args = map(lambda target: target.name, targets)
	del targets[:]
	yield ["bash", filename] + args

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

#################
# STACK TESTING #
#################

if os.environ.get("TESTSTACKS", False):
	def load_tests(loader, tests, pattern):
		suite = unittest.TestSuite()
		builds = {
		#
		# autotools stack
		# pre-requisites: build-essential, autoconf, automake
		#
			"https://github.com/orangeduck/ptest": ["example", "example2"],
			"https://github.com/andikleen/snappy-c": ["scmd", "sgverify", "verify"],
			"https://github.com/maxmind/geoip-api-c": ["apps/geoiplookup", "apps/geoiplookup6"],
			# automake fails due to a missing macro; issue reported
			#"https://github.com/vlm/asn1c": [],
			"https://github.com/git/git": ["git"],
			# not a standard process! no Makefile.am so install-sh touch'ed manually >=|
			#"https://github.com/php/php-src": [],
			"https://github.com/bagder/curl": ["src/curl"],
			"https://github.com/twitter/twemproxy": ["src/nutcracker"],
			# + libevent-dev, libncurses5-dev
			#"https://github.com/tmux/tmux": ["tmux"],
		}
		for git_url, target_paths in builds.items():
			class StackTest(unittest.TestCase):
				def setUp(self, git_url = git_url):
					"clone repository into temp dir"
					self.dirname = utils.mkdir()
					basename = os.path.basename(git_url)
					rootname, extname = os.path.splitext(basename)
					self.path = os.path.join(self.dirname, rootname)
					utils.check_call("git", "-C", self.dirname, "clone", git_url)
				def tearDown(self):
					"delete temp dir"
					utils.remove(self.dirname)
				def test_clean_compile(self, git_url = git_url, target_paths = target_paths):
					build.main("-C", self.path, "clean", "compile")
					for path in target_paths:
						self.assertTrue(os.path.exists(os.path.join(self.path, path)))
					if os.environ.get("PAUSE", False):
						print "---"
						print "Working on %s, dir to be cleaned: %s" % (git_url, self.dirname)
						raw_input("PAUSED, press enter to continue.")
			ldr = loader.loadTestsFromTestCase(StackTest)
			suite.addTests(ldr)
		ldr = loader.loadTestsFromTestCase(CoreTest)
		suite.addTests(ldr)
		return suite

if __name__ == "__main__":
	unittest.main(
		verbosity = 2,
		failfast = os.environ.get("FAILFAST", False))
