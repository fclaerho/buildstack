# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Detect and drive any source code build stack to reach well-known targets.

Usage:
  build [options] configure <toolid> [<vars>]
  build [options] get <packageid>
  build [options] <target>...
  build --version
  build --help

Options:
  -S <path>, --setupscript <path>  force python setup tools as build stack
  -C <path>, --directory <path>    common, set working directory
  -M <path>, --makefile <path>     force make as build stack
  -P <path>, --playbook <path>     force ansible as build stack
  -r <id>, --repository <id>       with get & publish: select repository
  -i <id>, --inventory <id>        with install: select inventory
  -p <ids>, --profiles <ids>       common, comma-separated build profiles
  -u <name>, --user <name>         common, build on behalf of the specified user
  -X <path>, --pom <path>          force maven as build stack
  -f <id>, --format <id>           with package: set format, use '-f help' to list ids
  -U, --uninstall                  with develop & install: undo
  -v, --verbose                    output commands
  -V, --version                    show version
  -h, --help                       show help
  -a, --all                        with clean: remove build artifacts

Targets:
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package [-f]: package code
  * publish [-r]: publish package to a repository
  * develop [-U]: [un]install locally in development mode
  * install [-U,-i]: [un]install locally or [un]provision inventory

Examples:
  Run unit tests then cleanup everything:
    $ build test clean -a
  Install deliverable as root:
    $ build install -u root
  For a python project, export xunit test report:
    $ build configure nose2 overwrite=yes
    $ build test
"""

import pkg_resources, subprocess, textwrap, glob, abc, sys, os, re

import docopt # 3rd-party

#############
# interface #
#############

class Target(object):

	def __init__(self, name, **kwargs):
		self.name = name
		self.kwargs = kwargs

	def __str__(self):
		return "%s %s" % (self.name, " ".join("%s=%s" % (k, v) for k, v in self.kwargs.items()))

	def __eq__(self, other):
		if isinstance(other, (str, unicode)):
			return self.name == other
		else:
			assert isinstance(other, Target), "%s: not a Target" % other
			return self.name == other.name and self.kwargs == other.kwargs

	def __getattr__(self, key):
		try:
			return self.kwargs[key]
		except KeyError:
			raise AttributeError(key)

class BuildError(Exception):

	def __str__(self):
		return "build error: %s" % " ".join(self.args)

DEVNULL = open(os.devnull, "w")

class BuildStack(object):
	"build stack interface"

	__metaclass__ = abc.ABCMeta

	def __init__(self, manifest_path, profileids = None, username = None, verbose = None):
		if not manifest_path:
			raise BuildError("missing manifest")
		elif not os.path.exists(manifest_path):
			raise BuildError("%s: no such file" % manifest_path)
		self.manifest_path = manifest_path
		self.profileids = profileids
		self.username = username
		self.verbose = verbose
		self.targets = []

	def check_call(self, args):
		if self.verbose:
			sys.stderr.write("\033[1;33m+ %s\033[0m\n" % " ".join(args))
		subprocess.check_call(args)

	@abc.abstractmethod
	def get(self, packageid, repositoryid = None):
		raise NotImplementedError()

	def clean(self, all = False):
		self.targets.append(Target("clean", all = all))

	def test(self):
		self.targets.append(Target("test"))

	def compile(self):
		self.targets.append(Target("compile"))

	def package(self, formatid = None):
		self.targets.append(Target("package", formatid = formatid))

	def publish(self, repositoryid = None):
		self.targets.append(Target("publish", repositoryid = repositoryid))

	def develop(self, uninstall = False):
		self.targets.append(Target("develop", uninstall = uninstall))

	def install(self, inventoryid = None, uninstall = False):
		self.targets.append(Target("install", inventoryid = inventoryid, uninstall = uninstall))

	@abc.abstractmethod
	def build(self):
		raise NotImplementedError()

##################
# implementation #
##################

class TargetError(BuildError):

	def __init__(self, target):
		super(TargetError, self).__init__("%s: unsupported target" % target.name)

class Make(BuildStack):

	def get(self, packageid):
		raise TargetError("make has no package management feature")

	def _make(self, *args):
		argv = ["make", "--file", self.manifest_path] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		self.check_call(argv)

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args.append("clean")
			elif target == Target("clean", all = True):
				args.append("distclean")
			elif target == "test":
				args.append("check")
			elif target == "compile":
				args.append("all")
			elif target == "package":
				args.append("dist")
			elif target == "install":
				args.append("uninstall" if target.uninstall else "install")
			else:
				raise TargetError(target)
		if args:
			self._make(*args)

class SetupTools(BuildStack):

	def _pip(self, *args):
		if not os.path.exists(".virtualenv"):
			self.check_call(("virtualenv", ".virtualenv"))
		argv = ["pip"] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		self.check_call(argv)

	def _setup(self, *args):
		argv = ["python", self.manifest_path] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		self.check_call(argv)

	def _twine(self, *args):
		argv = ["twine"] + list(args)
		if self.username:
			argv = ["sudo", "-u", self.username] + argv
		self.check_call(argv)

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
				del args[:]
				self.check_call(["rm", "-vrf", ".virtualenv", "dist", ".eggs", "nose2-junit.xml"] + glob.glob("*.egg-info") + glob.glob("*.pyc"))
			elif target == "test":
				setup = open("setup.py").read()
				if os.path.exists("nose2.cfg") and "nose2.collector.collector" not in setup:
					with open("setup.py.bak", "w") as f:
						f.write(setup)
					setup = re.sub("test_suite.*?,", "test_suite = \"nose2.collector.collector\",", setup)
					with open("setup.py", "w") as f:
						f.write(setup)
				args.append("test")
				# BUG:
				# - "python setup.py sdist test" does what's expected
				# - "python setup.py test sdist" does not run sdist
				self._setup(*args)
				del args[:]
			elif target == "compile":
				args.append("build")
			elif target == "package":
				def bdist_deb(args):
					raise NotImplementedError()
					#subprocess.check_call(("fakeroot", "dpkg-deb", "--build", path, self.path))
				def bdist_pkg(args):
					# *** EXPERIMENTAL ***
					args += ["bdist", "--format=tar"]
					self._setup(*args)
					del args[:]
					for path in glob.glob("dist/*.tar"):
						self.check_call(("mkdir", "-p", "dist/root"))
						self.check_call(("tar", "-C", "dist/root", "-xf", path))
						basename, extname = os.path.splitext(path)
						name, tail = basename.split("-", 1)
						version, _ = tail.split(".macosx", 1)
						identifier = "fr.fclaerhout.%s" % name
						self.check_call(("pkgbuild", basename + ".pkg", "--root", "dist/root", "--version", version, "--identifier", identifier))
						return
				func = {
					"sdist": lambda: args.append("sdist"),
					"sdist:zip": lambda: args.extend(["sdist", "--format=zip"]),
					"sdist:gztar": lambda: args.extend(["sdist", "--format=gztar"]),
					"sdist:bztar": lambda: args.extend(["sdist", "--format=bztar"]),
					"sdist:ztar": lambda: args.extend(["sdist", "--format=ztar"]),
					"sdist:tar": lambda: args.extend(["sdist", "--format=tar"]),
					"bdist": lambda: args.append("bdist"),
					"bdist:gztar": lambda: args.extend(["sdist", "--format=gztar"]), # unix default
					"bdist:ztar": lambda: args.extend(["sdist", "--format=ztar"]),
					"bdist:tar": lambda: args.extend(["sdist", "--format=tar"]),
					"bdist:zip": lambda: args.extend(["sdist", "--format=zip"]), # windows default
					"rpm": lambda: args.extend(["sdist", "--format=rpm"]),
					"pkgtool": lambda: args.extend(["sdist", "--format=pkgtool"]),
					"sdux": lambda: args.extend(["sdist", "--format=sdux"]),
					"wininst": lambda: args.extend(["sdist", "--format=wininst"]),
					"msi": lambda: args.extend(["sdist", "--format=msi"]),
					"deb": lambda: bdist_deb(args),
					"pkg": lambda: bdist_pkg(args),
				}
				if not hasattr(target, "formatid") or target.formatid is None:
					target.formatid = "sdist"
				elif target.formatid == "help":
					raise SystemExit("\n".join(func.keys()))
				func[target.formatid]()
			elif target == "publish":
				if args:
					self._setup(*args)
				del args[:]
				argv = ["upload"] + glob.glob("dist/*")
				if target.repositoryid:
					argv += ["-r", target.repositoryid]
				self._twine(*argv)
			elif target == Target("develop", uninstall = False):
				args.append("develop")
			elif target == Target("develop", uninstall = True):
				args += ["develop",  "--uninstall"]
			elif target == "install":
				if target.uninstall:
					if args:
						self._setup(*args)
					del args[:]
					self._pip("uninstall", os.path.basename(os.getcwd()))
				else:
					args.append("install")
			else:
				raise TargetError(target)
		if args:
			print "args=", args
			self._setup(*args)

class Ansible(BuildStack):

	def get(self, packageid, repositoryid = None):
		raise TargetError("ansible has no package management feature")

	def _play(self, *args):
		# user
		if self.username == "root":
			argv = ["--user", "root", "--ask-pass"] + list(args)
		elif self.username:
			argv = ["--user", self.username, "--sudo"] + list(args)
		else:
			argv = list(args)
		# tags
		if self.profileids:
			argv += ["--tags", self.profileids]
		self.check_call(["ansible-playbook", self.manifest_path] + argv)

	def build(self):
		for target in self.targets:
			if target == "test":
				self._play("--check") # dry run
			elif target.name == "install" and not target.uninstall:
				if target.inventoryid:
					if not os.path.exists(target.inventoryid):
						raise BuildError("%s: no such file" % target.inventoryid)
					self._play("--inventory-file", target.inventoryid)
				else:
					self._play()
			else:
				raise TargetError(target)

class Maven(BuildStack):
	"convention over configuration"

	def _mvn(self, *args):
		argv = ["mvn"] + list(args)
		if self.profileids:
			argv += ["--activate-profiles", self.profileids]
		self.check_call(argv)

	def get(self, packageid, repositoryid = None):
		argv = ["org.apache.maven.plugins:maven-dependency-plugin:2.1:get", "--define", "artifact=%s" % packageid]
		if repositoryid:
			argv += ["--define", "repoUrl=%s" % repositoryid]
		self._mvn(*argv)

	def build(self):
		args = []
		for target in self.targets:
			if target == Target("clean", all = False):
				args += ["clean"]
			elif target == "test":
				args += ["test"]
			elif target == "compile":
				args += ["compile"]
			elif target == "package":
				args += ["package"]
			elif target == "publish":
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

def get_build_stack(profileids = None, username = None, verbose = None):
	"autoguess the build stack to use depending on the build manifest found"
	stack = {
		"Gruntfile.coffee": Grunt,
		"playbook.yml": Ansible,
		"Gruntfile.js": Grunt,
		"build.xml": Ant,
		"setup.py": SetupTools,
		"Makefile": Make,
		"makefile": Make,
		"pom.xml": Maven,
	}
	for basename in stack:
		if os.path.exists(basename):
			return stack[basename](
				manifest_path = basename,
				profileids = profileids,
				username = username,
				verbose = verbose)
	raise BuildError("failed to detect build stack")

def configure(toolid, vars = None):
	tool = {
		"nose2": {
			"path": "nose2.cfg",
			"template": """
				# this is a generated file
				[unittest]
				plugins = nose2.plugins.junitxml
				[junit-xml]
				always-on = True
				[load_tests]
				always-on = True
			"""
		},
		"pypi": {
			"path": "~/.pypirc",
			"template": """
				# this is a generated file
				[distutils]
				index-servers = %(name)s
				[%(name)s]
				repository = %(url)s
				username = %(user)s
				password = %(pass)s
			"""
		},
	}
	if toolid == "help":
		print "\n".join(tool.keys())
	else:
		if not toolid in tool:
			raise BuildError("%s: unknown tool" % toolid)
		path = os.path.expanduser(tool[toolid]["path"])
		vars = dict(map(lambda item: item.split("="), vars.split(","))) if vars else {}
		if not os.path.exists(path) or vars.get("overwrite", "no") == "yes":
			with open(path, "w") as f:
				f.write(textwrap.dedent(tool[toolid]["template"]).lstrip() % vars)
		else:
			raise BuildError("%s: file already exists" % path)

def main(*args):
	opts = docopt.docopt(
		__doc__,
		argv = args or None,
		version = pkg_resources.require("build")[0].version)
	try:
		# change directory
		if opts["--directory"]:
			os.chdir(opts["--directory"])
		# instantiate build stack
		if opts["--makefile"]:
			bs = Make(
				manifest_path = opts["--makefile"],
				profileids = opts["--profiles"],
				username = opts["--user"],
				verbose = opts["--verbose"])
		elif opts["--setupscript"]:
			bs = SetupTools(
				manifest_path = opts["--setupscript"],
				profileids = opts["--profiles"],
				username = opts["--user"],
				verbose = opts["--verbose"])
		elif opts["--playbook"]:
			bs = Ansible(
				manifest_path = opts["--playbook"],
				profileids = opts["--profiles"],
				username = opts["--user"],
				verbose = opts["--verbose"])
		elif opts["--pom"]:
			bs = Maven(
				manifest_path = opts["--pom"],
				profileids = opts["--profiles"],
				username = opts["--user"],
				verbose = opts["--verbose"])
		else:
			bs = get_build_stack(
				profileids = opts["--profiles"],
				username = opts["--user"],
				verbose = opts["--verbose"])
		# handle use cases:
		if opts["configure"]:
			configure(opts["<toolid>"], opts["<vars>"])
		elif opts["get"]:
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
					bs.package(formatid = opts["--format"])
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
