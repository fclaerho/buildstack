# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Build stack helper.

Usage:
  code [options] get <packageid>
  code [options] <target>...
  code [options] (commit|log)
  code --version
  code --help

Options:
  -r <name>, --repository <name>  with publish, select upload repository
  -C <path>, --directory <path>   set working directory
  -i <path>, --inventory <path>   set inventory file
  -f <path>, --manifest <path>    set build manifest
  -u, --uninstall                 with develop and install, uninstall
  -v, --version                   show version
  -h, --help                      show help
  -a, --all                       with clean, remove build artifacts

"Code" detects and drives the project build stack to reach well-known targets:
  * get: install dependency in a virtual environment
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package: package code
  * publish [-r]: publish package into a specified repository
  * develop [-u]: install on localhost in development mode
  * install [-u,-i]: provision inventory
"""

# TODO: http://en.wikipedia.org/wiki/List_of_build_automation_software

import pkg_resources, subprocess, glob, abc, os

import docopt # 3rd-party

class VCS(object):
	"version control system interface"

	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod()
	def log(self):
		raise NotImplementedError()

	@abc.abstractmethod()
	def commit(self, push = True):
		raise NotImplementedError()

class Target(object):

	def __init__(self, name, **kwargs):
		self.name = name
		self.kwargs = kwargs

	def __str__(self):
		return "%s %s" % (self.name, " ".join("%s=%s" % (k, v) for k, v in self.kwargs.items()))

	def __eq__(self, other):
		return self.name == other.name and self.kwargs == other.kwargs

	def __getattr__(self, key):
		try:
			return self.kwargs[key]
		except KeyError:
			raise AttributeError(key)

class BuildError(Exception):

	def __str__(self):
		return "build error: %s" % " ".join(self.args)

class ManifestError(BuildError): pass

class BuildStack(object):
	"build stack interface"

	__metaclass__ = abc.ABCMeta

	def __init__(self, manifest_path):
		if not manifest_path:
			raise ManifestError("missing manifest")
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

	def publish(self, repository = None):
		self.targets.append(Target("publish", repository = repository))

	def develop(self, uninstall = False):
		self.targets.append(Target("develop", uninstall = uninstall))

	def install(self, inventory = None, uninstall = False):
		self.targets.append(Target("install", inventory = inventory, uninstall = uninstall))

	@abc.abstractmethod
	def build(self):
		raise NotImplementedError()

#########################
# concrete build stacks #
#########################

class Git(VCS):

	def log(self):
		subprocess.check_call((
			"git",
			"log",
			"--color",
			"--graph",
			"--pretty=format:%Cred%h%Creset: %C(yellow)%d%Creset %s %Cgreen - %an %cr%Creset",
			"--abbrev-commit"))

	def commit(self):
		subprocess.check_call(("git", "commit", "-a"))
		subprocess.check_call(("git", "push"))

class TargetError(BuildError):

	def __init__(self, target):
		super(TargetError, self).__init__("%s: unsupported target" % target.name)

class Make(BuildStack):

	def get(self, packageid):
		raise TargetError("get")

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args.append("clean")
			elif target == Target("clean", all = True):
				args.append("distclean")
			elif target == Target("test"):
				args.append("check")
			elif target == Target("compile"):
				args.append("all")
			elif target == Target("package"):
				args.append("dist")
			elif target.name == "install":
				args.append("uninstall" if target.uninstall else "install")
			else:
				raise TargetError(target)
		if args:
			subprocess.check_call(["make", "-f", self.manifest_path] + args)

class SetupTools(BuildStack):

	prefix = None

	def _get_path(self, basename):
		return os.path.join(filter(None, (self.prefix, name)))

	def _pip(self, *args):
		if not os.path.exists("env"):
			subprocess.check_call(("virtualenv", "_env"))
			self.prefix = "_env/bin"
		subprocess.check_call((self._get_path("pip"),) + args)

	def _setup(self, *args):
		subprocess.check_call((self._get_path("python"), self.manifest_path) + args)

	def _twine(self, *args):
		subprocess.check_call((self._get_path("twine"),) + args)

	def get(self, packageid): self._pip("install", packageid)

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args.append("clean")
			elif target == Target("clean", all = True):
				# build everything up to this point:
				args += ["clean", "--all"]
				self._setup(*args)
				# reset args:
				args = []
				# do deep clean:
				subprocess.check_call(["rm", "-vrf", "_env", "dist", ".eggs"] + glob.glob("*.egg-info") + glob.glob("*.pyc"))
			elif target == Target("test"):
				args.append("test")
			elif target == Target("compile"):
				args.append("build")
			elif target == Target("package"):
				args.append("sdist")
			elif target.name == "publish":
				# build everything up to this point:
				self._setup(*args)
				# reset args:
				args = []
				# do publish:
				_args = ["-r", target.repository] if target.repository else []
				_args += ["upload"] + glob.glob("dist/*")
				self._twine(*_args)
			elif target == Target("develop", uninstall = False):
				args.append("develop")
			elif target == Target("develop", uninstall = True):
				args += ["develop",  "--uninstall"]
			elif target.name == "install":
				if target.uninstall:
					# build everything up to this point:
					self._setup(*args)
					# reset args:
					args = []
					# do uninstall:
					self._pip("uninstall", os.path.basename(os.getcwd()))
				else:
					args.append("install")
			else:
				raise TargetError(target)
		if args:
			self._setup(*args)

class Ansible(BuildStack):

	def get(self, packageid):
		raise TargetError("get")

	def build(self):
		args = []
		for target in self.targets:
			if target.name == "install" and not target.uninstall:
				if target.inventory:
					args += ["-i", target.inventory]
				subprocess.check_call(["ansible-playbook", self.manifest_path] + args)
			else:
				raise TargetError(target)

###############
# entry point #
###############

def get_build_stack(manifest_path = None):
	map = {
		"Makefile": Make,
		"makefile": Make,
		"setup.py": SetupTools,
		"playbook.yml": Ansible,
	}
	if not manifest_path:
		for basename in map:
			if os.path.exists(basename):
				return map[basename](basename)
	else:
		return map[os.path.basename(manifest_path)](manifest_path)
	raise BuildError("failed to detect build stack")

def main(*argv):
	opts = docopt.docopt(
		__doc__,
		argv = argv or None,
		version = pkg_resources.require("code")[0].version)
	try:
		if opts["--directory"]:
			os.chdir(opts["--directory"])
		manifest_path = opts["--manifest"] or None
		vcs = Git()
		bs = get_build_stack(manifest_path)
		if opts["commit"]:
			vcs.commit()
		elif opts["log"]:
			vcs.log()
		elif opts["get"]:
			bs.get(opts["<packageid>"])
		else:
			for target in opts["<target>"]:
				{
					"clean": lambda: bs.clean(all = opts["--all"]),
					"test": bs.test,
					"compile": bs.compile,
					"package": bs.package,
					"publish": lambda: bs.publish(name = opts["--repository"]),
					"develop": lambda: bs.develop(uninstall = opts["--uninstall"]),
					"install": lambda: bs.install(inventory = opts["--inventory"], uninstall = opts["--uninstall"]),
				}[target]()
			bs.build()
	except (subprocess.CalledProcessError, BuildError) as exc:
		raise SystemExit("** fatal error! %s" % exc)

if __name__ == "__main__": main()
