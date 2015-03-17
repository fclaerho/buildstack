# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Build stack helper.

Usage:
  code [options] get <packageid>
  code [options] <target>...
  code --help

Options:
  -r <name>, --repository <name>  with publish, select publication repository
  -f <path>, --manifest <path>    set build manifest
  -u, --uninstall                 with develop and install, uninstall
  -v, --version                   show version
  -h, --help                      show help
  -a, --all                       with clean, remove build artifacts

"Code" detects the project build stack and drives it to reach well-known targets:
  * get: install dependency in a virtual environment
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package: package code
  * develop [-u]: install locally in development mode -- i.e. use current directory
  * install [-u]: install locally
  * publish [-r]: publish package into a specified repository
"""

import pkg_resources, subprocess, glob, abc, os

import docopt # 3rd-party

class ManifestError(Exception): pass

class BuildError(Exception): pass

class BuildStack(object):

	__metaclass__ = abc.ABCMeta

	def __init__(self, manifest_path):
		if not manifest_path:
			raise ManifestError("failed to detect manifest")
		elif not os.path.exists(manifest_path):
			raise ManifestError("%s: no such file" % manifest_path)
		self.manifest_path = manifest_path

	@abc.abstractmethod
	def get(self, packageid):
		raise NotImplementedError("cannot get package")

	@abc.abstractmethod
	def clean(self, all = False):
		raise NotImplementedError("cannot clean")

	@abc.abstractmethod
	def test(self):
		raise NotImplementedError("cannot test")

	@abc.abstractmethod
	def compile(self):
		raise NotImplementedError("cannot compile")

	@abc.abstractmethod
	def package(self):
		raise NotImplementedError("cannot package")

	@abc.abstractmethod
	def develop(self, uninstall = False):
		raise NotImplementedError("cannot develop")

	@abc.abstractmethod
	def install(self, uninstall = False):
		raise NotImplementedError("cannot install")

	@abc.abstractmethod
	def publish(self, name = None):
		raise NotImplementedError("cannot publish")

#########################
# concrete build stacks #
#########################

class Make(BuildStack):

	def _make(self, *args):
		subprocess.check_call(("make", "-f", self.manifest_path) + args)

	def __init__(self, manifest_path = None):
		if not manifest_path:
			for basename in ("Makefile", "makefile"):
				if os.path.exists(basename):
					manifest_path = basename
		else:
			raise ManifestError
		super(Make, self).__init__(manifest_path)
		try:
			self._make("--dry-run") # check manifest
		except:
			raise ManifestError

	def get(self, packageid):
		raise BuildError("%s: make stack has no package manager" % packageid)

	def clean(self, all = False):
		if all:
			self._make("distclean")
		else:
			self._make("clean")

	def test(self): self._make("check")

	def compile(self): self._make("all")

	def package(self): self._make("dist")

	def develop(self, uninstall = False):
		raise BuildError("make stack has no develop mode")

	def install(self, uninstall = False):
		if uninstall:
			self._make("uninstall")
		else:
			self._make("install")

	def publish(self, name = None):
		raise BuildError("make stack has no publication manager")

class SetupTools(BuildStack):

	prefix = ""

	def __init__(self, manifest_path):
		if not manifest_path:
			if os.path.exists("setup.py"):
				manifest_path = "setup.py"
		super(SetupTools, self).__init__(manifest_path)

	def _pip(self, *args):
		if not os.path.exists("env"):
			subprocess.check_call(("virtualenv", "_env"))
			self.prefix = "_env/bin"
		subprocess.check_call(("_env/bin/pip",) + args)

	def _setup(self, *args):
		subprocess.check_call((os.path.join(self.prefix, "python"), self.manifest_path) + args)

	def _twine(self, *args):
		subprocess.check_call((os.path.join(self.prefix, "twine"),) + args)

	def get(self, packageid): self._pip("install", packageid)

	def clean(self, all = False):
		args = ["clean"]
		if all:
			args += ["--all"]
		self._setup(*args)
		subprocess.check_call(("rm", "-rf", "_env"))

	def test(self): self._setup("test")

	def compile(self):
		raise NotImplementedError()

	def package(self): self._setup("sdist")

	def develop(self, uninstall = False):
		if uninstall:
			self._setup("develop", "--uninstall")
		else:
			self._setup("develop")

	def install(self, uninstall = False):
		if uninstall:
			self._pip("uninstall", os.path.basename(os.getcwd()))
		else:
			self._setup("install")

	def publish(self, name = None):
		args = ["-r", name] if name else []
		args += ["upload"] + glob.glob("dist/*")
		self._twine(*args)

###############
# entry point #
###############

class DetectionError(Exception): pass

def get_build_stack(manifest_path = None):
	for cls in (Make, SetupTools):
		try:
			return (cls)(manifest_path)
		except ManifestError:
			continue
	raise DetectionError("failed to detect build stack")

def main():
	opts = docopt.docopt(__doc__, version = pkg_resources.require("code")[0].version)
	try:
		manifest_path = opts["--manifest"] or None
		bs = get_build_stack(manifest_path)
		if opts["get"]:
			bs.get(opts["<packageid>"])
		else:
			for target in opts["<target>"]:
				{
					"clean": lambda: bs.clean(opts["--all"]),
					"test": lambda: bs.test(),
					"compile": lambda: bs.compile(),
					"package": lambda: bs.package(),
					"develop": lambda: bs.develop(opts["--uninstall"]),
					"install": lambda: bs.install(opts["--uninstall"]),
					"publish": lambda: bs.publish(opts["--repository"]),
				}[target]()
	except (subprocess.CalledProcessError, DetectionError, BuildError) as exc:
		raise SystemExit("** fatal error! %s: %s" % (type(exc).__name__, exc))

if __name__ == "__main__": main()
