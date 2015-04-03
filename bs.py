# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Detect and drive any source code build stack to reach well-known targets.

Usage:
  bs [options] get <packageid>
  bs [options] <target>...
  bs --version
  bs --help

Options:
  -S <path>, --setupscript <path>  force python setup tools as build stack
  -C <path>, --directory <path>    set working directory
  -M <path>, --makefile <path>     force make as build stack
  -P <path>, --playbook <path>     force ansible as build stack
  -r <id>, --repository <id>       with get & publish: select repository
  -i <id>, --inventory <id>        with install: select inventory
  -p <ids>, --profiles <ids>       comma-separated build profiles
  -u <name>, --user <name>         build on behalf of the specified user
  -X <path>, --pom <path>          force maven as build stack
  -f <id>, --format <id>           set package format
  -U, --uninstall                  with develop & install: undo
  -v, --version                    show version
  -h, --help                       show help
  -a, --all                        with clean: remove build artifacts

Targets:
  * get [-r]: install dependency from a repository -- use a VE if possible
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package [-f]: package code
  * publish [-r]: publish package to a repository
  * develop [-U]: [un]install locally in development mode
  * install [-U,-i]: [un]install locally or [un]provision inventory

Examples:
  $ bs test clean -a
  $ bs install -u root
"""

import pkg_resources, subprocess, glob, abc, os

import docopt # 3rd-party

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

class BuildStack(object):
	"build stack interface"

	__metaclass__ = abc.ABCMeta

	def __init__(self, manifest_path, username = None, profileids = None):
		if not manifest_path:
			raise BuildError("missing manifest")
		elif not os.path.exists(manifest_path):
			raise BuildError("%s: no such file" % manifest_path)
		self.manifest_path = manifest_path
		self.profileids = profileids
		self.username = username
		self.targets = []

	@abc.abstractmethod
	def get(self, packageid, repositoryid = None):
		raise NotImplementedError()

	def clean(self, all = False):
		self.targets.append(Target("clean", all = all))

	def test(self):
		self.targets.append(Target("test"))

	def compile(self):
		self.targets.append(Target("compile"))

	def package(self):
		self.targets.append(Target("package"))

	def publish(self, repositoryid = None):
		self.targets.append(Target("publish", repositoryid = repositoryid))

	def develop(self, uninstall = False):
		self.targets.append(Target("develop", uninstall = uninstall))

	def install(self, inventoryid = None, uninstall = False):
		self.targets.append(Target("install", inventoryid = inventoryid, uninstall = uninstall))

	@abc.abstractmethod
	def build(self):
		raise NotImplementedError()

#########################
# concrete build stacks #
#########################

class TargetError(BuildError):

	def __init__(self, target):
		super(TargetError, self).__init__("%s: unsupported target" % target.name)

class Make(BuildStack):

	def get(self, packageid):
		raise TargetError("make has no package management feature")

	def _make(self, *args):
		argv = ["make", "-f", self.manifest_path] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		subprocess.check_call(argv)

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
			self._make(*args)

class SetupTools(BuildStack):

	prefix = None

	def _get_path(self, basename):
		if self.prefix:
			return os.path.join(self.prefix, basename)
		else:
			return basename

	def _pip(self, *args):
		if not os.path.exists(".virtualenv"):
			subprocess.check_call(("virtualenv", ".virtualenv"))
			self.prefix = ".virtualenv/bin"
		argv = [self._get_path("pip")] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		subprocess.check_call(argv)

	def _setup(self, *args):
		argv = [self._get_path("python"), self.manifest_path] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		subprocess.check_call(argv)

	def _twine(self, *args):
		argv = [self._get_path("twine")] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		subprocess.check_call(argv)

	def get(self, packageid, repositoryid = None):
		argv = ["install", packageid]
		if repositoryid:
			argv += ["-i", repositoryid]
		self._pip(*argv)

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args.append("clean")
			elif target == Target("clean", all = True):
				args += ["clean", "--all"]
				self._setup(*args)
				args = []
				subprocess.check_call(["rm", "-vrf", ".virtualenv", "dist", ".eggs"] + glob.glob("*.egg-info") + glob.glob("*.pyc"))
			elif target == Target("test"):
				args.append("test")
			elif target == Target("compile"):
				args.append("build")
			elif target == Target("package"):
				args.append("sdist")
			elif target.name == "publish":
				if args:
					self._setup(*args)
				args = []
				argv = ["upload"] + glob.glob("dist/*")
				if target.repositoryid:
					argv += ["-r", target.repositoryid]
				self._twine(*argv)
			elif target == Target("develop", uninstall = False):
				args.append("develop")
			elif target == Target("develop", uninstall = True):
				args += ["develop",  "--uninstall"]
			elif target.name == "install":
				if target.uninstall:
					if args:
						self._setup(*args)
					args = []
					self._pip("uninstall", os.path.basename(os.getcwd()))
				else:
					args.append("install")
			else:
				raise TargetError(target)
		if args:
			self._setup(*args)

class Ansible(BuildStack):

	def get(self, packageid, repositoryid = None):
		raise TargetError("ansible has no package management feature")

	def _play(self, *args):
		# user
		if self.username == "root":
			argv = ["-u", "root", "--ask-pass"] + list(args)
		elif self.username:
			argv = ["-u", self.username, "--sudo"] + list(args)
		else:
			argv = list(args)
		# tags
		if self.profileids:
			argv += ["--tags", self.profileids]
		subprocess.check_call(["ansible-playbook", self.manifest_path] + argv)

	def build(self):
		for target in self.targets:
			if target == Target("test"):
				self._play("--check") # dry run
			elif target.name == "install" and not target.uninstall:
				if target.inventoryid:
					if not os.path.exists(target.inventoryid):
						raise BuildError("%s: no such file" % target.inventoryid)
					self._play("-i", target.inventoryid)
				else:
					self._play()
			else:
				raise TargetError(target)

class Maven(BuildStack):
	"convention over configuration"

	def _mvn(self, *args):
		argv = ["mvn"] + list(args)
		if self.profileids:
			argv += ["-P", self.profileids]
		subprocess.check_call(argv)

	def get(self, packageid, repositoryid = None):
		argv = ["org.apache.maven.plugins:maven-dependency-plugin:2.1:get", "-Dartifact=%s" % packageid]
		if repositoryid:
			argv += ["-DrepoUrl=%s" % repositoryid]
		self._mvn(*argv)

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args += ["clean"]
			elif target == Target("test"):
				args += ["test"]
			elif target == Target("compile"):
				args += ["compile"]
			elif target == Target("package"):
				args += ["package"]
			elif target == Target("publish"):
				args += ["deploy"]
			elif target.name == "install" and not target.uninstall:
				args += ["install"]
			else:
				raise TargetError(target)
		if args:
			self._mvn(*args)

class Ant(BuildStack): pass

class Grunt(BuildStack): pass

###############
# entry point #
###############

def get_build_stack(username = None, profileids = None):
	"autoguess the build stack to use depending on the build manifest found"
	map = {
		"Gruntfile.coffee": Grunt,
		"playbook.yml": Ansible,
		"Gruntfile.js": Grunt,
		"build.xml": Ant,
		"setup.py": SetupTools,
		"Makefile": Make,
		"makefile": Make,
		"pom.xml": Maven,
	}
	for basename in map:
		if os.path.exists(basename):
			return map[basename](
				manifest_path = basename,
				username = username,
				profileids = profileids)
	raise BuildError("failed to detect build stack")

def main(*argv):
	opts = docopt.docopt(
		__doc__,
		argv = argv or None,
		version = pkg_resources.require("sc")[0].version)
	try:
		if opts["--directory"]:
			os.chdir(opts["--directory"])
		if opts["--makefile"]:
			bs = Make(
				manifest_path = opts["--makefile"],
				username = opts["--user"],
				profileids = opts["--profiles"])
		elif opts["--setupscript"]:
			bs = SetupTools(
				manifest_path = opts["--setupscript"],
				username = opts["--user"],
				profileids = opts["--profiles"])
		elif opts["--playbook"]:
			bs = Ansible(
				manifest_path = opts["--playbook"],
				username = opts["--user"],
				profileids = opts["--profiles"])
		elif opts["--pom"]:
			bs = Maven(
				manifest_path = opts["--pom"],
				username = opts["--user"],
				profileids = opts["--profiles"])
		else:
			bs = get_build_stack(
				username = opts["--user"],
				profileids = opts["--profiles"])
		if opts["get"]:
			bs.get(
				packageid = opts["<packageid>"],
				repositoryid = opts["--repository"])
		else:
			for target in opts["<target>"]:
				if target == "clean":
					bs.clean(all = opts["--all"])
				elif target == "test":
					bs.test()
				elif target == "compile":
					bs.compile()
				elif target == "package":
					bs.package()
				elif target == "publish":
					bs.publish(repositoryid = opts["--repository"])
				elif target == "develop":
					bs.develop(uninstall = opts["--uninstall"])
				elif target == "install":
					bs.install(inventoryid = opts["--inventory"], uninstall = opts["--uninstall"])
				else:
					raise BuildError("%s: unknown target" % target)
			bs.build()
	except (subprocess.CalledProcessError, BuildError) as exc:
		raise SystemExit("** fatal error! %s" % exc)

if __name__ == "__main__": main()
