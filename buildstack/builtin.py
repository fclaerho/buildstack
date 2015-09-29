# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

### EXPERIMENTAL -- TO BE REWORKED ###

"""
An opinionated pocket build tool.

Phases:
  clean                               wipe out build workspace
  test < compile < package < install  install lifecycle
                           < publish  publish lifecycle
  test < compile < check              check lifecycle
  uninstall                           uninstall package(s) locally

Manifest Syntax:
  Build expects a manifest specifying the targets for each phase.
  A target is specified in a section named [<phase>:<name>] having attributes.
  The <name> is optional for clean, install or uninstall-phased targets.
  Common attributes:
  - 'paths': optional static list of source paths possibly prefixed by tags
  - 'policy': by default, if a target has no static source paths, it uses
    the previous phase output paths. 'policy' allows to change this
    behavior. It may take the following values:
    - 'discard': use static source paths only
    - 'append': merge static source paths and previous phase output paths
    - 'reset': use previous phase output paths only
  Test attributes and tags:
  - 'dep@': tagged path is a test dependency
  - 'mode': 'failfast', run all tests otherwise
  Compile attributes and tags:
  - 'main@': tagged path contains the entry point
  - 'res@': tagged path is a resource artifact
    - with python: all content is copied into the generated module "resource"
    - other languages: not yet supported
  - 'extension': artifact extension; required on windows if autoguess fails
  - 'version': for compile-phased targets, specify a language version to use
  - 'command': optional compilation command line, support $< and $@ variables
  Check tags: same as Test.
  Package attributes:
  - 'conf@': tagged path is a system-wide configuration artifact
  - 'author', required
  - 'version', required
  - 'services': json dict of dicts, each dict specifying a service:
    - 'uid': service username or uid
    - 'argv': additional commandline arguments
    - 'path': service daemon path
    - 'description': service description
  - 'identifier', required, maven-like group id
  - 'description', required
  - 'architecture', required
  Install attributes:
  - 'command': optional deployment command line, support $< variable
  Uninstall attributes:
  - 'identifier': required, see Package
  Other attributes are copied as it.

Manifest Example:
  | [test:module]
  | paths: test/test_hello.py
  |
  | [compile:hello]
  | paths: main@source/hello.py
  |
  | [package:hello]
  | author: foo@example.com
  | version: 1.0
  | identifier: com.example.hello
  | description: hello world
  | architecture: all
  |
  | [install:]
  |
  | [uninstall:]
  | identifier: com.example.hello

Development 101:
  Grab the latest source code.
  You may add phases with the Phase object, in on_flush().
  Phases can be linked together to create lifecycles.
  Each phase must have an associated class, derived from Target.
  A Target subclass must implement, at least, the build() method.
"""

import ConfigParser, subprocess, tempfile, shutil, urllib, stat, abc, md5, os

#############
# templates #
#############

CONTROL = """
Package: %(name)s
Version: %(version)s
Maintainer: %(author)s
Description: %(description)s
Architecture: %(architecture)s
"""

SYSV = """
#!/bin/sh
### BEGIN INIT INFO
# Provides:          %(name)s
# Required-Start:    $local_fs $network $named $time $syslog
# Required-Stop:     $local_fs $network $named $time $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Description:       %(description)s
### END INIT INFO

PIDFILE="/var/run/%(name)s.pid"
DAEMON="%(path)s"
ARGV="%(argv)s"
UID="%(uid)s"

status() {
	if start-stop-daemon --status --pidfile $PIDFILE; then
		echo "service is running" >&2
	else
		echo "service is not running" >&2
	fi
}

start() {
	start-stop-daemon\
		--start\
		--pidfile $PIDFILE\
		--make-pidfile\
		--chuid $UID\
		--background\
		--exec $DAEMON -- $ARGV
}

stop() {
	start-stop-daemon --stop --pidfile $PIDFILE
}

case "$1" in
	status)
		status
		;;
	start)
		start
		;;
	stop)
		stop
		;;
	restart)
		stop
		start
		;;
	*)
		echo "Usage: $0 {status|start|stop|restart}"
esac
"""

POSTINST = """
#!/bin/sh
# copyrigh (c) 2014 fclaerhout.fr, released under the MIT license.
# service post-install template.

set -e -x

if ! grep -q %(username)s /etc/password; then
	echo "adding user %(username)s..."
	adduser --disabled-login --disabled-password --gecos "" %(username)s
else
	echo "user %(username)s already exists..."
fi

service %(srvname)s restart
"""

###########
# helpers #
###########

DEVNULL = open(os.devnull, "w")

def init_platform():
	"""
	Copypasted from https://github.com/fclaerho/copypasta
	guess host platform and set global variables accordingly
	"""
	import subprocess, platform, os
	global WINDOWS, DARWIN, LINUX, DEBIAN, CENTOS, UBUNTU, UNIX
	WINDOWS = platform.uname()[0] == "Windows"
	DARWIN = platform.uname()[0] == "Darwin"
	LINUX = platform.uname()[0] == "Linux"
	DEBIAN = LINUX and os.path.exists("/etc/debian_version")
	CENTOS = LINUX and os.path.exists("/etc/centos-release")
	DEVNULL = open(os.devnull, "w")
	UBUNTU = LINUX\
		and subprocess.call(("which", "lsb_release"), stdout = DEVNULL) == 0\
		and subprocess.check_output(("lsb_release", "-i", "-s")).strip() == "Ubuntu"
	UNIX = DARWIN or DEBIAN or UBUNTU or CENTOS

def _exec(cmd, *args, **kwargs):
	"""
	Check $cmd is installed, run it and return its output on sucess.
	Raise AssertionError if not installed or subprocess.CalledProcessError on failure.
	"""
	shell = kwargs.get("shell", False)
	if not shell:
		if WINDOWS:
			if not subprocess.call(("where", cmd), stdout = DEVNULL):
				raise IOError("%s: not installed" % cmd)
		elif UNIX:
			if not subprocess.call(("which", cmd), stdout = DEVNULL):
				raise IOError("%s: not installed" % cmd)
		else:
			raise NotImplementedError("unsupported platform")
	args = cmd if shell else (cmd,) + args
	#print "executing:", args
	return subprocess.check_output(args, **kwargs)

class Node(object):
	"abstract filesystem node"

	def __init__(self, path, parent = None):
		if parent:
			assert os.path.basename(path) == path, "%s: expected basename" % path
			self.basename = path
			self.parent = parent
			self.path = self._get_path
		else:
			self.path = os.path.abspath(path)

	@property
	def _get_path(self):
		return os.path.join(self.parent.path, self.basename)

	def exists(self):
		return os.path.exists(self.path)

class Dir(Node):

	def create(self):
		if not self.exists():
			os.makedirs(self.path)
		return self

	def delete(self):
		if self.exists():
			shutil.rmtree(self.path)
		return self

	def Dir(self, basename):
		return Dir(basename, parent = self)

	def File(self, basename):
		return File(basename, parent = self)

	def TempDir(self):
		return TempDir(parent = self)

class TempDir(Dir):

	def __init__(self, parent):
		parent.create()
		self._path = tempfile.mkdtemp(dir = parent.path)

	@property
	def path(self):
		return self._path

class File(Node):
	"file node, defer parent creation when needed"

	def set_executable(self):
		assert self.exists(), "%s: no such file" % self.path
		os.chmod(
			self.path,
			os.stat(self.path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

	def read(self):
		with open(self.path, "r") as fp:
			return fp.read()

	def write(self, data, append = False):
		self.parent.create()
		with open(self.path, "a" if append else "w") as fp:
			fp.write(data)
		return self

	def copy_from(self, path):
		self.parent.create()
		shutil.copy(path, self.path)
		return self

	def zip_from(self, *paths):
		self.parent.create()
		if UNIX:
			_exec("zip", "--junk-paths", self.path, *paths)
		else:
			raise NotImplementedError("unsupported platform")
		return self

	def pkg_from(self, path, version, identifier):
		self.parent.create()
		if DARWIN:
			_exec("pkgbuild", self.path, "--root", path, "--version", version, "--identifier", identifier)
		else:
			raise NotImplementedError("unsupported platform")
		return self

	def deb_from(self, path):
		self.parent.create()
		if DEBIAN or UBUNTU:
			_exec("fakeroot", "dpkg-deb", "--build", path, self.path)
		else:
			raise NotImplementedError("unsupported platform")
		return self

	def jar_from(self, path, entry):
		self.parent.create()
		if UNIX:
			_exec("jar", "cfe", self.path, entry, "-C", path, ".")
		else:
			raise NotImplementedError("unsupported platform")
		return self

##############
# interfaces #
##############

class HMap(object):
	"hold md5 map of a file set"

	def __init__(self, root, name, *paths):
		self.file = root.File("%s.hmap" % name)
		self.map = {}
		for path in paths:
			path = os.path.abspath(path) # normalize path
			with open(path, "r") as fp:
				self.map[path] = md5.new(fp.read()).digest()

	def save(self):
		if self.map:
			self.file.write("%s" % self.map)
		return self

	def load(self):
		assert not self.map, "map not empty, cannot (over)load content"
		if self.file.exists():
			self.map = eval(self.file.read())
		return self

	def __eq__(self, other):
		return self.map == other.map

	def __ne__(self, other):
		return not (self == other)

class Target(object):

	__metaclass__ = abc.ABCMeta

	phony = False # makefile jargon: if set, the target outputs no artifact

	def __init__(self, name, root, *paths, **attributes):
		self.name = name
		self.root = root
		self.paths = ()
		for path in paths:
			assert os.path.exists(path), "%s: no such file" % path
			self.paths += (path,)
		self.basename = name
		self.attributes = attributes

	def __getitem__(self, key):
		return getattr(self, key) if hasattr(self, key) else self.attributes[key]

	def __getattr__(self, key):
		try:
			return self.attributes[key]
		except KeyError:
			raise AttributeError(key)

	def update(self, *paths):
		"build and return artifact (rebuild if it doesn't exist or is outdated)"
		paths = {
			"default": lambda *paths: self.paths or paths,
			"discard": lambda *paths: self.paths,
			"append": lambda *paths: self.paths + paths,
			"reset": lambda *paths: paths,
		}[getattr(self, "policy", "default")](*paths)
		if self.phony:
			self.build(*paths) # no outfile for phony targets
		else:
			oldhmap = HMap(self.root, self.basename).load()
			newhmap = HMap(self.root, self.basename, *paths)
			outfile = self.root.File(self.basename)
			if outfile.exists() and newhmap == oldhmap:
				print "%s: up-to-date" % self.name
			else:
				newhmap.save()
				self.build(outfile, *paths)
				assert outfile.exists(), "%s: target not built" % self.name
			return outfile.path

	@abc.abstractmethod
	def build(self, outfile, *paths): pass

class Phase(object):

	_instances = {}

	@classmethod
	def get(cls, name):
		assert name in cls._instances, "%s: no such phase" % name
		return cls._instances[name]

	def __init__(self, name, model, previous = None):
		self.name = name
		self.model = model
		self.previous = previous
		self._instances[name] = self

	def run(self, target_name, targets, *paths):
		if self.previous:
			paths = self.get(self.previous).run(None, targets, *paths)
		def is_selected(tgt):
			return isinstance(tgt, self.model) and (not target_name or tgt.name == target_name)
		try:
			return list(tgt.update(*paths) for tgt in targets if is_selected(tgt)) or paths
		except Exception as e:
			raise type(e)("at phase %s: %s" % (self.name, e))

##################
# implementation #
##################

class Clean(Target):

	phony = True

	def build(self, *paths):
		self.root.delete()

class _Test(Target):

	def run_python_tests(self, *paths):
		mods = []
		suite = unittest.TestSuite()
		for path in getattr(self, "dep", ()):
			dirname = os.path.abspath(os.path.dirname(path))
			if not dirname in sys.path:
				sys.path.append(dirname)
		for path in filter(lambda path: path not in getattr(self, "dep", ()), paths):
			with open(path) as fp:
				basename = os.path.basename(path)
				rootname, _ = os.path.splitext(basename)
				mods.append(types.ModuleType(rootname))
				exec fp.read() in mods[-1].__dict__
				suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mods[-1]))
		failfast = getattr(self, "mode", "default") == "failfast"
		assert unittest.TextTestRunner(failfast = failfast, verbosity = 2).run(suite).wasSuccessful(), "test(s) failed"

	def run_tests(self, *paths):
		if all(path.endswith(".py") for path in paths):
			self.run_python_tests(*paths)
		else:
			raise NotImplementedError("%s: unsupported test sources" % self)

class Test(_Test):

	def build(self, outfile, *paths):
		self.run_tests(*paths)
		outfile.write("ok") # TODO: write xunit report

class Check(_Test):

	phony = True

	def build(self, *paths):
		self.run_tests(*paths)

class Compile(Target):

	def __init__(self, *args, **kwargs):
		super(Compile, self).__init__(*args, **kwargs)
		if WINDOWS:
			if self.paths and self.policy in ("default", "discard"):
				if all(path.endswith(".py") for path in self.paths):
					self.extension = "py"
				elif all(path.endswith(".java") for path in self.paths):
					self.extension = "jar"
			assert hasattr(self, "extension"), "missing extension attribute, see --help"
			self.basename = "%s.%s" % (self.basename, self.extension)

	def _build_with_command(self, outfile, *paths):
		subprocess.check_call(
			self.command.replace("$@", pipes.quote(outfile.path)).replace("$<", " ".join(map(pipes.quote, paths))),
			shell = True)

	def _build_python_executable_archive(self, outfile, *paths):
		paths = list(paths)
		if hasattr(self, "main"):
			paths[paths.index(*self.main)] = self.root.TempDir().File("__main__.py").copy_from(*self.main).path
		f = self.root.TempDir().File("resource.py")
		for path in getattr(self, "res", ()):
			rootname, _ = os.path.splitext(os.path.basename(path))
			with open(path, "r") as fp:
				f.write("%s = %s\n\n" % (rootname, repr(fp.read())), append = True)
			paths[paths.index(path)] = f.path
		version = getattr(self, "version", "2.7")
		assert version in ("2.4" , "2.5", "2.6", "2.7", "3"), "%s: unsupported python version" % version
		if UNIX:
			f = self.root.File("%s.zip" % self.name).zip_from(*paths)
			outfile.write("#!/usr/bin/python%s\n%s" % (version, f.read()))
			outfile.set_executable()
		elif WINDOWS:
			outfile.zip_from(*paths)

	def _build_java_executable_archive(self, outfile, *paths):
		d = self.root.Dir("%s_classes" % self.name).create()
		_exec("javac", "-d", d.path, *paths)
		e, _ = os.path.splitext(os.path.basename(*self.main))
		if UNIX:
			f = self.root.File("%s.jar" % self.name).jar_from(d.path, entry = e)
			outfile.write("#!/usr/bin/java -jar\n" + f.read())
			outfile.set_executable()
		elif WINDOWS:
			outfile.jar_from(d.path, entry = e)

	def _build_go_executable(self, outfile, *paths):
		_exec("go", "build", "-o", outfile.path, *paths)

	def _build_haskell_executable(self, outfile, *paths):
		_exec("ghc", "-o", outfile.path, *paths)

	def _build_c_executable(self, outfile, *paths):
		_exec("cc", "-O3", "-Wall", "-Werror", "-o", outfile.path, *paths)

	def build(self, outfile, *paths):
		if hasattr(self, "command"):
			return self._build_with_command(outfile, *paths)
		elif all(path.endswith(".py") or path in getattr(self, "res", ()) for path in paths):
			assert\
				hasattr(self, "main") or any(os.path.basename(path) == "__main__.py" for path in paths),\
				"missing entry point, either have a __main__.py file or prefix a path with main@"
			return self._build_python_executable_archive(outfile, *paths)
		elif all(path.endswith(".java") for path in paths):
			assert hasattr(self, "main"), "missing entry point, prefix a path with main@"
			return self._build_java_executable_archive(outfile, *paths)
		elif all(path.endswith(".go") for path in paths):
			return self._build_go_executable(outfile, *paths)
		elif all(path.endswith(".hs") for path in paths):
			return self._build_haskell_executable(outfile, *paths)
		elif all(path.endswith(".c") or path.endswith(".h") for path in paths):
			return self._build_c_executable(outfile, *paths)
		else:
			raise NotImplementedError("unsupported code sources")

class Package(Target):

	def __init__(self, *args, **kwargs):
		super(type(self), self).__init__(*args, **kwargs)
		rev = _exec("git", "rev-parse", "--short", "HEAD").strip()
		self.basename = "%s_%s~%s_%s" % (
			self.name,
			self.version,
			rev,
			self.architecture)
		self.sysname = os.uname()[0]
		if DARWIN:
			self.basename += ".pkg"
		elif CENTOS:
			self.basename += ".rpm"
		elif DEBIAN or UBUNTU:
			self.basename += ".deb"
		else:
			raise NotImplementedError("unsupported platform")

	def build(self, outfile, *paths):
		paths = list(paths)
		pkgdir = self.root.Dir("%s_root" % self.name)
		if hasattr(self, "conf"):
			if UNIX:
				etcdir = pkgdir.Dir("etc").Dir(self.name)
				etcdir.create()
				for path in self.conf:
					shutil.copy(path, etcdir.path)
					del paths[paths.index(path)]
			else:
				raise NotImplementedError("conf@ tag not yet unsupported on this platform")
		bindir = pkgdir.Dir("usr").Dir("local").Dir("bin")
		bindir.create()
		for path in paths:
			shutil.copy(path, bindir.path)
		# handle services...
		if hasattr(self, "services"):
			services = json.loads(self.services)
			if DEBIAN:
				inidir = pkgdir.Dir("etc").Dir("init.d")
				postinst = pkgdir.Dir("DEBIAN").File("postinst")
				for key, srv in services.items():
					for attr in ("uid", "argv", "path"):
						assert attr in srv, "missing %s.%s attribute" % (key, attr)
					vars = {
						"name": key,
						"uid": srv["uid"],
						"argv": srv["argv"],
						"path": srv["path"],
						"description": srv.get("description", self.description),
					}
					inidir.File(key).write(SYSV % vars)
					postinst.write(POSTINST % vars, append = True)
					postinst.set_executable()
			else:
				raise NotImplementedError("services attribute not yet supported on this platform")
		# ...then manifest and final packaging
		if DARWIN:
			for attr in ("version", "identifier"):
				assert hasattr(self, attr), "missing %s attribute" % attr
			outfile.pkg_from(
				path = pkgdir.path,
				version = self.version,
				identifier = self.identifier)
		elif DEBIAN or UBUNTU:
			control = pkgdir.Dir("DEBIAN").File("control")
			for attr in ("name", "version", "author", "description", "architecture"):
				assert hasattr(self,attr), "missing %s attribute" % attr
			control.write(CONTROL % self)
			outfile.deb_from(pkgdir.path)
		else:
			raise NotImplementedError("unsupported platform")

class Install(Target):

	phony = True

	def _custom_install(self, *paths):
		subprocess.check_call(
			self.command.replace("$<", " ".join(map(pipes.quote, paths))),
			shell = True)

	def _local_install(self, *paths):
		for path in paths:
			if DARWIN:
				assert path.endswith(".pkg"), "unexpected package type"
				_exec("sudo", "installer", "-pkg", path, "-target", "/")
			elif DEBIAN or UBUNTU:
				assert path.endswith(".deb"), "unexpected package type"
				_exec("sudo", "dpkg", "--install", path)
			else:
				raise NotImplementedError("install target not yet supported on this platform")

	def build(self, *paths):
		if hasattr(self, "command"):
			self._custom_install(*paths)
		else:
			self._local_install(*paths)

class Uninstall(Target):

	phony = True

	def build(self, *paths):
		if DARWIN:
			paths = list("/%s" % line for line in _exec("pkgutil", "--files", self.identifier).splitlines())
			# delete files first...
			for path in filter(os.path.isfile, paths):
				_exec("sudo", "rm", "-i", path)
			# ...then delete empty directories
			for path in sorted(filter(os.path.isdir, paths), reverse = True):
				if not os.listdir(path):
					_exec("sudo", "rmdir", path)
					print "deleted empty directory", path
			_exec("sudo", "pkgutil", "--forget", self.identifier)
		elif DEBIAN or UBUNTU:
			_exec("sudo", "apt-get", "remove", "--purge", self.identifier.split(".")[-1])
		else:
			raise NotImplementedError("unsupported platform")

#########
# entry #
#########

SOURCE_PATH = "source"
VENDOR_PATH = "vendor"
TARGET_PATH = "target"

def init(root):
	"generate dummy hello world workspace"
	if not os.path.exists("build"):
		if WINDOWS:
			path = subprocess.check_output(("where", "build")).strip()
		elif UNIX:
			path = subprocess.check_output(("which", "build")).strip()
		else:
			raise NotImplementedError("unsupported platform")
		shutil.copyfile(path, "./build")
		shutil.copymode(path, "./build")
	elif UNIX\
	and not subprocess.call(("test", "-e", "./build"))\
	and not subprocess.call(("which", "-s", "build"))\
	and distutils.version.StrictVersion(subprocess.check_output(("build", "-v")))\
		> distutils.version.StrictVersion(subprocess.check_output(("./build", "-v"))):
		print "** warning: the local build version is outdated"
	for basename in (SOURCE_PATH, VENDOR_PATH):
		if not os.path.exists(basename):
			os.mkdir(basename)
		assert os.path.isdir(basename), "%s: expected directory" % basename
	if not os.path.exists("%s/hello.py" % SOURCE_PATH):
		with open("%s/hello.py" % SOURCE_PATH, "w+") as fp:
			fp.write("print \"hello world!\"")
	if not os.path.exists(".gitignore"):
		with open(".gitignore", "w+") as fp:
			fp.write(".DS_Store\n*.pyc\n*.o\n%s\n" % os.path.relpath(root.path))
	if not os.path.exists(".git"):
		_exec("git", "init")
	if not os.path.exists("build.ini"):
		with open("build.ini", "w+") as fp:
			fp.write("[compile:hello]\npaths: main@source/hello.py\n")

def on_get(filename, targets, repositoryid, requirementid):
	if ".git" in requirementid:
		# e.g. git://foo.com/bar.git
		if requirementid.endswith(".git"):
			basename = os.path.basename(requirementid)
			rootname, _ = os.path.splitext(basename)
			_exec("git", "submodule", "add", requirementid, "%s/%s" % (VENDOR_PATH, rootname))
		# e.g. git://foo.com/bar.git/source/main.c
		else:
			_, path = requirementid.split(".git/")
			remote = requirementid.replace(path, "")
			_exec("git archive --remote=%s HEAD %s | tar -x --strip-components %i -C %s" % (remote, path, path.count("/"), VENDOR_PATH), shell = True)
	elif requirementid.startswith("python:"):
		_, package = requirementid.split(":", 1)
		_exec(
			"easy_install", "--install-dir", VENDOR_PATH, "--exclude-scripts", "--always-unzip", package,
			env = {"PYTHONPATH": VENDOR_PATH})
		_exec("rm", "-f", "%s/easy-install.pth" % VENDOR_PATH, "%s/site.py" % VENDOR_PATH, "%s/site.pyc" % VENDOR_PATH)
	else:
		raise NotImplementedError("%s: unsupported requirementid" % requirementid)

def parse_targets(url, root):
	"parse manifest and return reified targets"
	parser = ConfigParser.ConfigParser()
	parser.readfp(urllib.urlopen(url))
	parser.add_section("clean:")
	for section in parser.sections():
		try:
			assert ":" in section, "invalid section name, expected <phase>:<name>"
			phase, name = section.split(":")
			cls = Phase.get(phase).model
			assert cls.phony or name, "missing name for non-phony target"
			attributes = {k: v for k, v in parser.items(section) if k != "paths"}
			paths = []
			if parser.has_option(section, "paths"):
				for path in parser.get(section, "paths").split():
					if "@" in path:
						tag, path = path.split("@", 1)
						if tag in attributes:
							attributes[tag] += [path]
						else:
							attributes[tag] = [path]
					paths.append(path)
			yield cls(name or None, root, *paths, **attributes)
		except Exception as e:
			raise type(e)("in section [%s]: %s" % (section, e))

def on_flush(filename, targets):
	init_platform()
	root = Dir(TARGET_PATH)
	Phase("clean", model = Clean)
	Phase("test", model = Test)
	Phase("compile", model = Compile, previous = "test")
	Phase("package", model = Package, previous = "compile")
	Phase("install", model = Install, previous = "package")
	Phase("check", model = Check, previous = "compile")
	Phase("uninstall", model = Uninstall)
	available_targets = list(parse_targets(filename, root = root))
	while targets:
		target = targets.pop(0)
		phase, _, name = target.name.partition(":")
		Phase.get(phase).run(name, available_targets)
	raise StopIteration
	yield # force this function to be a generator

MANIFEST = {
	"filenames": ("build.ini",),
	"on_get": on_get,
	"on_flush": on_flush,
}
