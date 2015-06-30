# copyright (c) 2015 fclaerhout.fr, all rights reserved

"""
Detect and drive a source code build stack to reach well-known targets.

Usage:
  build [options] configure (<toolid>|help) [<vars>]
  build [options] <target>...
  build --help

Options:
  -C <path>, --directory <path>  set working directory
  -m <str>, --message <str>      set commit message on release
  -f <path>, --file <path>       set build manifest path
  -p <id>, --profile <id>        set build profile
  -c, --no-colors                disable ANSI color codes
  -v, --verbose                  trace execution
  -h, --help                     show help

Where <target> is one of:
  * get:<id>             install requirement
  * clean[:<id>]         delete files out of the identified scope
  * compile              compile code
  * test                 run unit tests
  * package[:<id>]       package code [in the identified format]
  * publish[:<id>]       publish package [to the identified repository]
  * [un]install[:<id>]   [un]install locally [or [un]provision inventory]
  * release[:<id>] [-m]  bump project version, commit and tag

Examples:
  To compile the project:
    $ build compile
  To run unit tests then clean-up:
    $ build test clean
  Clean-up, compile, package and install:
    $ build clean compile package install

Use '~/build.json' to customize commands:
  {
    "<profileid>|all": {
      "<command>": {
        "before": [[argv...]...], # list of commands to run before
        "append": [argv...],      # extra arguments to append
        "after": [[argv...]...],  # list of commands to run after
        "path": "<path>"          # custom image path
      }...
    }...
  }
"""

import textwrap, fnmatch, glob, json, sys, os

import buildstack, docopt # 3rd-party

def blue(string):
	return "\033[1;34m%s\033[0m" % string

def red(string):
	return "\033[1;31m%s\033[0m" % string

DEVNULL = open(os.devnull, "w")

TRACEFP = DEVNULL

def trace(*strings):
	TRACEFP.write(blue("+ %s\n") % " ".join(strings))

def check_call(args, trace = lambda *args: None, _cache = {}):
	"""
	Copypasted from https://github.com/fclaerho/copypasta
	Trace and execute command or raise IOError if it is not available or fails.
	v20150625A
	"""
	import subprocess, platform
	trace(*args)
	image = args[0]
	if not image in _cache:
		which = "where" if platform.uname()[0] == "Windows" else "which"
		_cache[image] = subprocess.call((which, image), stdout = DEVNULL, stderr = DEVNULL)
	if _cache[image] != 0:
		raise IOError("%s is unavailable, please install it" % image)
	try:
		subprocess.check_call(args)
	except subprocess.CalledProcessError as exc:
		raise IOError(*exc.args)

def parse_file(path, extname = None, default = None):
	"""
	Copypasted from https://github.com/fclaerho/copypasta
	Return parsed file content or $default if it does not exist, raise IOError otherwise.
	Support json, ini and text files.
	v20150630A
	"""
	import ConfigParser, json, os
	path = os.path.expanduser(path)
	if os.path.exists(path):
		rootname, _extname = os.path.splitext(path)
		with open(path, "r") as fp:
			if extname == ".ini" or _extname == ".ini":
				parser = ConfigParser.ConfigParser()
				if not parser.readfp(fp):
					raise IOError("%s: unreadable file" % path)
				_dict = {}
				for section in parser.sections():
					_dict[section] = {key: value for key, value in parser.items(section)}
				return _dict
			elif extname == ".json" or _extname == ".json":
				try:
					return json.load(fp)
				except ValueError as exc:
					raise IOError("%s: json parse error (%s)" % (path, exc))
			else:
				return fp.read()
	else:
		return default

def chdir(path, trace = lambda *args: None):
	"""
	Copypasted from https://github.com/fclaerho/copypasta
	Trace and change of current working directory.
	v20150625A
	"""
	import os
	trace("chdir", path)
	os.chdir(os.path.expanduser(path))

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

	def __init__(self, customization = None, profileid = None, filename = None, dirname = None):
		self.customization = customization or {}
		self.profileid = profileid
		self.filename = filename and os.path.basename(filename)
		if dirname:
			chdir(dirname)
		# resolve manifest:
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
		if not manifests:
			raise BuildError("no supported build stack detected")
		elif len(manifests) > 1:
			raise BuildError("%s: multiple build stacks detected" % ", ".join(map(lambda m: m["name"], manifests)))
		else:
			self.manifest, = manifests
		for key in ("name", "filenames"):
			if not key in self.manifest:
				raise BuildError("%s: missing required manifest property" % key)
		self.targets = Targets()
		trace("using '%s' build stack" % self.manifest["name"])

	def _check_call(self, args):
		_dict = self.customization.get(self.profileid or "all", {}).get(args[0], {})
		args = list(args)
		args[0] = _dict.get("path", args[0])
		argslist =\
			_dict.get("before", [])\
			+ [args + _dict.get("append", [])]\
			+ _dict.get("after", [])
		for args in argslist:
			check_call(args, trace = trace)

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
						assert canflush, "%s: cannot flush from this target" % key
						self.flush()
					elif isinstance(res, (list, tuple)):
						self._check_call(res)
					else: # assume res is an error object
						raise BuildError("%s: %s: %s" % (self.manifest["name"], name, res))
			else: # the manifest explicitly declares this target as unsupported
				raise BuildError("%s: %s: unsupported target" % (self.manifest["name"], name))
		elif default == "stack": # stack target and let the on_flush handler deal with it
			self.targets.append(name, **kwargs)
		elif default == "fail":
			raise BuildError("%s: %s: unhandled target" % (self.manifest["name"], name))

	def get(self, requirementid):
		self._handle_target(
			"get",
			default = "fail",
			requirementid = requirementid)

	def clean(self, scopeid = None):
		"delete generated files"
		if scopeid == "tracked":
			print "removing untracked files"
			self.flush()
			if os.path.exists(".git"):
				self._check_call(("git", "clean", "--force", "-d", "-x"))
			elif os.path.exists(".hg"):
				self._check_call(("hg", "purge", "--config", "extensions.purge="))
			else:
				raise BuildError("unknown VCS, cannot remove untracked files") # NOTE: add svn-cleanup
		else:
			self._handle_target("clean", scopeid = scopeid)

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

	def install(self, inventoryid = None, uninstall = False):
		"deploy target objects in production mode"
		self._handle_target(
			"install",
			inventoryid = inventoryid,
			uninstall = uninstall)

	def release(self, typeid, message):
		"increment project version and commit"
		self._handle_target(
			"release",
			typeid = typeid,
			message = message)

	def flush(self):
		self._handle_target("flush", canflush = False, default = "fail")
		assert not self.targets, "%s: lingering unhandled target(s)" % self.manifest["name"]

def configure(toolid, vars = None):
	tool = {}
	for manifest in buildstack.manifests:
		tool.update(manifest.get("tool", {}))
	if toolid == "help":
		name_width = max(map(len, tool.keys()))
		path_width = max(map(lambda key: len(tool[key]["path"]), tool.keys()))
		def print_help(key):
			vars = tool[key]["defaults"]
			for name in tool[key]["required_vars"]:
				vars[name] = "REQUIRED"
			print\
				blue(key.rjust(name_width)),\
				tool[key]["path"].center(path_width),\
				"%s" % ",".join("%s=%s" % (key, vars[key]) for key in vars)
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
	opts = docopt.docopt(__doc__, argv = args or None)
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
				customization = parse_file("~/build.json", default = None),
				profileid = opts["--profile"],
				filename = opts["--file"],
				dirname = opts["--directory"])
			for target in opts["<target>"]:
				if target.startswith("get:"):
					bs.get(requirementid = target.split(":")[1])
				elif target.startswith("clean"):
					bs.clean(scopeid = target.partition(":")[2])
				elif target == "compile":
					bs.compile()
				elif target == "test":
					bs.test()
				elif target.startswith("package"):
					bs.package(formatid = target.partition(":")[2])
				elif target.startswith("publish"):
					bs.publish(repositoryid = target.partition(":")[2])
				elif target.startswith("install") or target.startswith("uninstall"):
					bs.install(
						inventoryid = target.partition(":")[2],
						uninstall = target == "uninstall")
				elif target.startswith("release"):
					bs.release(typeid = target.partition(":")[2], message = opts["--message"])
				else:
					raise BuildError("%s: unknown target" % target)
				bs.flush()
	except (NotImplementedError, BuildError, IOError) as exc:
		# Possible runtime errors are caught and nicely formatted for the user (no stacktrace!)
		# SystemExit(str) is builtin and returns a status code of 1, this is good enough.
		# Anything else has to be debugged and the stacktrace is therefore kept for you.
		raise SystemExit(red(exc))

if __name__ == "__main__": main()
