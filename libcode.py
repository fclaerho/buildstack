# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Build stack helper.

Usage:
  code [options] get <packageid>
  code [options] <target>...
  code --help

Options:
  -r <name>, --repository <name>  with publish, select upload repository
  -C <path>, --directory <path>   set working directory
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
  * develop [-u]: install on localhost in development mode
  * install [-u]: install on localhost
  * publish [-r]: publish package into a specified repository
"""

import pkg_resources, subprocess, glob, abc, os

import docopt # 3rd-party

class Target(object):

	def __init__(self, name, **kwargs):
		self.name = name
		self.kwargs = kwargs

	def __eq__(self, other):
		return self.name == other.name and self.kwargs == other.kwargs

	def __getattr__(self, key):
		try:
			self.kwargs[key]
		except KeyError:
			raise AttributeError(key)

class ManifestError(Exception): pass

class BuildError(Exception):

	def __str__(self):
		return "build error: %s" % (self.args,)

class BuildStack(object):

	__metaclass__ = abc.ABCMeta

	def __init__(self, manifest_path):
		if not manifest_path:
			raise ManifestError("failed to detect manifest")
		elif not os.path.exists(manifest_path):
			raise ManifestError("%s: no such file" % manifest_path)
		self.manifest_path = manifest_path
		self.targets = []

	@abc.abstractmethod
	def get(self, packageid):
		raise NotImplementedError()

	def clean(self, all = False):
		self.targets.append(Target("clean", all = all))

	def test(self):
		self.targets.append(Target("test"))

	def compile(self):
		self.targets.append(Target("compile"))

	def package(self):
		self.targets.append(Target("package"))

	def develop(self, uninstall = False):
		self.targets.append(Target("develop", uninstall = uninstall))

	def install(self, uninstall = False):
		self.targets.append(Target("install", uninstall = uninstall))

	def publish(self, name = None):
		self.targets.append(Target("publish", name = name))

	@abc.abstractmethod
	def build(self):
		raise NotImplementedError()

#########################
# concrete build stacks #
#########################

class TargetError(BuildError):

	def __init__(self, target):
		super(TargetError, self).__init__("%s: unexpected target" % target.name)

class Make(BuildStack):

	def __init__(self, manifest_path = None):
		if not manifest_path:
			for basename in ("Makefile", "makefile"):
				if os.path.exists(basename):
					manifest_path = basename
		# FIXME: check this is a Makefile, raise ManifestError otherwise
		super(Make, self).__init__(manifest_path)

	def get(self, packageid):
		raise BuildError("make stack has no package manager")

	def develop(self, *argv, **kwargs):
		raise BuildError("make stack has no develop mode")

	def publish(self, *argv, **kwargs):
		raise BuildError("make stack has no publication manager")

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean"):
				args.append("clean")
			elif target == Target("clean", all = True):
				args.append("distclean")
			elif target == Target("test"):
				args.append("check")
			elif target == Target("compile"):
				args.append("all")
			elif target == Target("package"):
				args.append("dist")
			elif target == Target("install"):
				args.append("install")
			elif target == Target("install", uninstall = True):
				args.append("uninstall")
			else:
				raise TargetError(target)
		if args:
			subprocess.check_call(["make", "-f", self.manifest_path] + args)

class SetupTools(BuildStack):

	prefix = ""

	def __init__(self, manifest_path):
		if not manifest_path:
			if os.path.exists("setup.py"):
				manifest_path = "setup.py"
		# FIXME: check this is a setuptools manifest, raise ManifestError otherwise
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

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean"):
				args.append("clean")
			elif target == Target("clean", all = True):
				args += ["clean", "--all"]
				subprocess.check_call(["rm", "-vrf", "_env"] + glob.glob("*.egg-info") + glob.glob("*.pyc"))
			elif target == Target("test"):
				args.append("test")
			elif target == Target("compile"):
				args.append("build")
			elif target == Target("package"):
				args.append("sdist")
			elif target == Target("develop"):
				args.append("develop")
			elif target == Target("develop", uninstall = True):
				args += ["develop",  "--uninstall"]
			elif target == Target("install"):
				args.append("install")
			elif target == Target("install", uninstall = True):
				# build everything up to this point:
				self._setup(*args)
				# reset args:
				args = []
				# do uninstall:
				self._pip("uninstall", os.path.basename(os.getcwd()))
			elif target == Target("publish"):
				# build everything up to this point:
				self._setup(*args)
				# reset args:
				args = []
				# do publish:
				_args = ["-r", name] if name else []
				_args += ["upload"] + glob.glob("dist/*")
				self._twine(*_args)
			else:
				raise TargetError(target)
		if args:
			self._setup(*args)

class Maven(BuildStack):

	def __init__(self, manifest_path = None):
		if not manifest_path:
			if os.path.exists("pom.xml"):
				manifest_path = "pom.xml"
		super(SetupTools, self).__init__(manifest_path)

###############
# entry point #
###############

def get_build_stack(manifest_path = None):
	for cls in (Make, SetupTools):
		try:
			return (cls)(manifest_path)
		except ManifestError:
			continue
	raise BuildError("failed to detect build stack")

def main(*argv):
	opts = docopt.docopt(__doc__, argv = argv, version = pkg_resources.require("code")[0].version)
	try:
		if opts["--directory"]:
			os.chdir(opts["--directory"])
		manifest_path = opts["--manifest"] or None
		bs = get_build_stack(manifest_path)
		if opts["get"]:
			bs.get(opts["<packageid>"])
		else:
			for target in opts["<target>"]:
				{
					"clean": lambda: bs.clean(all = opts["--all"]),
					"test": bs.test,
					"compile": bs.compile,
					"package": bs.package,
					"develop": lambda: bs.develop(uninstall = opts["--uninstall"]),
					"install": lambda: bs.install(uninstall = opts["--uninstall"]),
					"publish": lambda: bs.publish(name = opts["--repository"]),
				}[target]()
			bs.build()
	except (subprocess.CalledProcessError, BuildError) as exc:
		raise SystemExit("** fatal error! %s" % exc)

if __name__ == "__main__": main()
