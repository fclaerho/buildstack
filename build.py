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
  -v, --verbose                  trace execution
  -h, --help                     display full help text
  --no-color                     disable colored output

Where <target> is one of:
  * get:<id>             install requirement(s)
  * clean                delete generated files
  * compile              compile code
  * test                 run unit tests
  * package[:<id>]       package code [in the identified format]
  * publish[:<id>]       publish package [to the identified repository]
  * [un]install[:<id>]   [un]install locally [or [un]provision inventory]
  * release[:<id>] [-m]  bump project version, commit and tag

Examples:
  To compile the project in subdir foo:
    $ build -C foo/ compile
  To run unit tests, clean-up and release:
    $ build test clean release:patch
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

import textwrap, fnmatch, glob, os

import buildstack, docopt, utils # 3rd-party

class Error(utils.Error): pass

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

class BuildStack(object):

	def __init__(self, customization = None, profileid = None, filename = None, dirname = None):
		self.customization = customization or {}
		self.profileid = profileid
		self.filename = filename and os.path.basename(filename)
		if dirname:
			utils.chdir(dirname)
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
			raise Error("no supported build stack detected")
		elif len(manifests) > 1:
			raise Error("/".join(map(lambda m: m["name"], manifests)), "multiple build stacks detected")
		else:
			self.manifest, = manifests
		for key in ("name", "filenames"):
			if not key in self.manifest:
				raise Error(key, "missing required manifest property")
		self.targets = Targets()
		utils.trace("using '%s' build stack" % self.manifest["name"])

	def _check_call(self, args):
		_dict = self.customization.get(self.profileid or "all", {}).get(args[0], {})
		args = list(args)
		args[0] = os.path.expanduser(_dict.get("path", args[0]))
		argslist =\
			_dict.get("before", [])\
			+ [args + _dict.get("append", [])]\
			+ _dict.get("after", [])
		for args in argslist:
			utils.check_call(*args)

	def _handle_target(self, name, canflush = True, default = "stack", **kwargs):
		handler = self.manifest.get("on_%s" % name, default)
		if handler is None:
			# the manifest explicitly declares this target as unsupported
			raise Error(self.manifest["name"], name, "unsupported target")
		elif handler == "stack": # stack target and let the on_flush handler deal with it
			self.targets.append(name, **kwargs)
		elif handler == "fail":
			raise Error(self.manifest["name"], name, "unhandled target")
		elif handler == "purge":
			self.flush()
			if os.path.exists(".git"):
				self._check_call(("git", "clean", "--force", "-d", "-x"))
			elif os.path.exists(".hg"):
				self._check_call(("hg", "purge", "--config", "extensions.purge="))
			else:
				raise Error("unknown VCS, cannot remove untracked files") # NOTE: add svn-cleanup
		elif callable(handler):
			for res in (handler)(
				profileid = self.profileid,
				filename = self.filename,
				targets = self.targets,
				**kwargs):
				if isinstance(res, (list, tuple)):
					if res[0].startswith("@"):
						eval(res[0][1:])(*res[1:])
					else:
						self._check_call(res)
				elif res == "flush":
					assert canflush, "%s: cannot flush from this target" % key
					self.flush()
				else: # res is an error object
					raise Error(self.manifest["name"], name, res)
		else:
			assert False, "%s: invalid target handler" % handler

	def get(self, requirementid):
		"get required dependencies"
		self._handle_target(
			"get",
			default = "fail",
			requirementid = requirementid)

	def clean(self):
		"delete generated files"
		self._handle_target("clean")

	def compile(self):
		"compile source code into target objects"
		self._handle_target("compile")

	def test(self):
		"run unit tests"
		self._handle_target("test")

	def package(self, formatid = None):
		"bundle target objects with metadata"
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
		if self.targets:
			self._handle_target("flush", canflush = False, default = "fail")
		if self.targets:
			raise Error(self.manifest["name"], "lingering unhandled target(s) -- please report this bug")

def configure(toolid, vars = None):
	tools = {}
	for manifest in buildstack.manifests:
		tools.update(manifest.get("tools", {}))
	if toolid == "help":
		name_width = max(map(len, tools))
		path_width = max(map(lambda key: len(tools[key]["path"]), tools))
		for key in tools:
			required = ", ".join(tools[key]["required_vars"])
			optional = ", ".join("%s=%s" % (k, v) for k,v in tools[key]["defaults"].items())
			print\
				utils.magenta(key.rjust(name_width)),\
				tools[key]["path"].center(path_width),\
				required,\
				("[%s]" % optional) if optional else ""
	else:
		suffix = ", run 'build configure help' for details"
		if not toolid in tools:
			raise Error(toolid, "unknown tool" + suffix)
		path = os.path.expanduser(tools[toolid]["path"])
		vars = dict(tools[toolid]["defaults"], **(dict(map(lambda item: item.split("="), vars.split(","))) if vars else {}))
		if not os.path.exists(path) or vars.get("overwrite", "no") == "yes":
			try:
				text = textwrap.dedent(tools[toolid]["template"]).lstrip() % vars
			except KeyError as exc:
				raise Error(" ".join(exc.args), "missing required variable" + suffix)
			with open(path, "w") as fp:
				fp.write(text)
			utils.trace("%s: template instantiated" % path)
		else:
			raise Error(path, "file already exists, use overwrite=yes to overwrite it")

def main(*args):
	opts = docopt.docopt(
		doc = __doc__,
		argv = args or None)
	try:
		if opts["--no-color"]:
			utils.disable_colors()
		if opts["--verbose"]:
			utils.enable_tracing()
		if opts["configure"]:
			configure(
				toolid = opts["<toolid>"],
				vars = opts["<vars>"])
		else:
			bs = BuildStack(
				customization = utils.parse_file("~/build.json", default = None),
				profileid = opts["--profile"],
				filename = opts["--file"],
				dirname = opts["--directory"])
			for target in opts["<target>"]:
				if target.startswith("get:"):
					bs.get(requirementid = target.split(":")[1])
				elif target == "clean":
					bs.clean()
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
					raise Error(target, "unknown target")
				bs.flush()
	except utils.Error as exc:
		raise SystemExit(utils.red(exc))

if __name__ == "__main__": main()
