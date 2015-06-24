# copyright (c) 2015 fclaerhout.fr, all rights reserved

"""
Detect and drive a source code build stack to reach well-known targets.

Usage:
  build [options] configure (<toolid>|help) [<vars>]
  build [options] get <packageid>
  build [options] <target>...
  build --version
  build --help

Options:
  -C <path>, --directory <path>  set working directory
  -r <id>, --repository <id>     with 'get' and 'publish': select repository
  -i <id>, --inventory <id>      with 'install': select inventory
  -e <args>, --extra <args>      arguments appended to build stack invocation
  -f <path>, --file <path>       set build manifest path
  -p <id>, --profile <id>        set build profile
  -F <id>, --format <id>         with 'package': set format, use '-f help' to list ids
  -u, --uninstall                with 'develop' and 'install': uninstall
  -c, --no-colors                disable ANSI color codes
  -v, --verbose                  output executed commands
  -V, --version                  show version
  -h, --help                     show help
  -a, --all                      with 'clean': remove build artifacts

<target> values:
  * clean [-a]: delete objects generated during the build
  * compile: compile code, for non-interpreted languages
  * test: run unit tests
  * package [-f]: package code
  * publish [-r]: publish package to a repository
  * develop [-U]: [un]install locally in development mode
  * install [-U,-i]: [un]install locally or [un]provision inventory

Examples:
  Any stack, to compile the project:
    $ build compile
  Any stack, run unit tests then cleanup everything:
    $ build test clean -a
  Ansible, deploy as root:
    $ build install -e "--user root --ask-pass"
  Python, fetch dependencies:
    $ build get requirements.txt
"""

import pkg_resources, subprocess, textwrap, fnmatch, glob, sys, os

import buildstack, docopt # 3rd-party

def blue(string):
	return "\033[34m%s\033[0m" % string

def red(string):
	return "\033[31m%s\033[0m" % string

DEVNULL = open(os.devnull, "w")

TRACEFP = DEVNULL

def trace(*strings):
	TRACEFP.write(blue("+ %s\n") % " ".join(strings))

def _chdir(path):
	trace("chdir", path)
	os.chdir(os.path.expanduser(path))

def _check_call(args, _cache = {}):
	trace(*args)
	image = args[0]
	if not image in _cache:
		_cache[image] = subprocess.call(("which", image), stdout = DEVNULL, stderr = DEVNULL)
	if _cache[image] != 0:
		raise IOError("%s is unavailable, please install it" % image)
	subprocess.check_call(args)

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
			return None

class Targets(list):

	def append(self, name, **kwargs):
		super(Targets, self).append(Target(name, **kwargs))

class BuildError(Exception):

	def __str__(self):
		return "build error: %s" % " ".join(self.args)

class BuildStack(object):

	def __init__(self, profileid = None, extraargs = None, filename = None, dirname = None):
		self.profileid = profileid
		self.extraargs = extraargs or ()
		self.filename = filename and os.path.basename(filename)
		_chdir(dirname)
		manifests = []
		if self.filename:
			# find all stacks able to handle this manifest:
			for manifest in buildstack.manifests:
				for pattern in manifest["filenames"]:
					if fnmatch.fnmatch(self.filename, pattern):
						manifests.append(manifest)
						break
		else:
			# otherwise try all filenames declared by all stacks:
			for manifest in buildstack.manifests:
				for pattern in manifest["filenames"]:
					filenames = glob.glob(pattern)
					if filenames:
						self.filename = filenames[0] # pick first match
						manifests.append(manifest)
						break
		# assess there's exactly one stack found, or fail:
		if not manifests:
			raise BuildError("no supported build stack detected")
		elif len(manifests) > 1:
			raise BuildError("%s: multiple build stacks detected" % ",".join(map(lambda m: m["name"], manifests)))
		else:
			self.manifest, = manifests
		for key in ("name", "filenames"):
			if not key in self.manifest:
				raise BuildError("%s: missing required manifest property" % key)
		self.targets = Targets()
		trace("%s build stack ready" % self.manifest["name"])

	def _check_call(self, args):
		args += self.extraargs
		_check_call(args)

	def _handle_target(self, name, canflush = True, default = "stack", **kwargs):
		key = "on_%s" % name
		if key in self.manifest:
			if self.manifest[key]:
				assert callable(self.manifest[key]), "%s: %s: not callable" % (self.manifest["name"], key)
				for res in self.manifest[key](
					profileid = self.profileid,
					filename = self.filename,
					targets = self.targets,
					**kwargs):
					if res == "flush":
						assert canflush
						self.flush()
					elif isinstance(res, (list, tuple)):
						self._check_call(res)
					else: # assume res is an error object
						raise BuildError("%s: %s: %s" % (self.manifest["name"], name, res))
			else: # the manifest explicitly declares this target as unsupported
				raise BuildError("%s: %s: unsupported target" % (self.manifest["name"], name))
		elif default == "stack":
			self.targets.append(name, **kwargs)
		elif default == "fail":
			raise BuildError("%s: %s: unhandled target" % (self.manifest["name"], name))

	def clean(self, all = False):
		"delete intermediary objects. If all is true, delete target objects as well"
		self._handle_target("clean", all = all)

	def compile(self):
		"compile source code into target objects"
		self._handle_target("compile")

	def test(self):
		"run unit tests"
		self._handle_target("test")

	def package(self, formatid = None):
		"package target objects"
		self._handle_target(
			"package",
			formatid = formatid)

	def publish(self, repositoryid = None):
		"publish package to the target repository"
		self._handle_target(
			"publish",
			repositoryid = repositoryid)

	def develop(self, uninstall = False):
		"deploy target objects in development mode"
		self._handle_target(
			"develop",
			uninstall = uninstall)

	def install(self, inventoryid = None, uninstall = False):
		"deploy target objects in production mode"
		self._handle_target(
			"install",
			inventoryid = inventoryid,
			uninstall = uninstall)

	def flush(self):
		self._handle_target("flush", canflush = False, default = "stack")
		assert not self.targets, "%s: lingering unhandled target(s)" % self.manifest["name"]

	def get(self, packageid, repositoryid = None):
		self._handle_target(
			"get",
			canflush = False,
			default = "fail",
			packageid = packageid,
			repositoryid = repositoryid)

def configure(toolid, vars = None):
	tool = {}
	for manifest in buildstack.manifests:
		tool.update(manifest.get("tool", {}))
	if toolid == "help":
		def print_help(key):
			vars = tool[key]["defaults"]
			for name in tool[key]["required_vars"]:
				vars[name] = "REQUIRED"
			print blue(key) + " %s" % ",".join("%s=%s" % (key, vars[key]) for key in vars)
		map(print_help, tool.keys())
	else:
		if not toolid in tool:
			raise BuildError("%s: unknown tool" % toolid)
		path = os.path.expanduser(tool[toolid]["path"])
		vars = dict(tool[toolid]["defaults"], **(dict(map(lambda item: item.split("="), vars.split(","))) if vars else {}))
		if not os.path.exists(path) or vars.get("overwrite", "no") == "yes":
			try:
				text = textwrap.dedent(tool[toolid]["template"]).lstrip() % vars
			except KeyError as exc:
				raise BuildError("%s: missing required variable" % exc)
			with open(path, "w") as f:
				f.write(text)
		else:
			raise BuildError("%s: file already exists" % path)

def main(*args):
	opts = docopt.docopt(
		__doc__,
		argv = args or None,
		version = pkg_resources.require("build")[0].version)
	try:
		if opts["--no-colors"]:
			global blue, red
			blue = red = lambda s: s
		if opts["--verbose"]:
			global TRACEFP
			TRACEFP = sys.stderr
		if opts["configure"]:
			configure(
				toolid = opts["<toolid>"],
				vars = opts["<vars>"])
		else:
			bs = BuildStack(
				profileid = opts["--profile"],
				extraargs = opts["--extra"] and opts["--extra"].split(),
				filename = opts["--file"],
				dirname = opts["--directory"])
			if opts["get"]:
				bs.get(
					packageid = opts["<packageid>"],
					repositoryid = opts["--repository"])
			else:
				for target in opts["<target>"]:
					if target == "clean":
						bs.clean(all = opts["--all"])
					elif target == "compile":
						bs.compile()
					elif target == "test":
						bs.test()
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
				bs.flush()
	except (subprocess.CalledProcessError, BuildError) as exc:
		raise SystemExit(red(exc))

if __name__ == "__main__": main()

