# copyright (c) 2015 fclaerhout.fr, all rights reserved

"""
Detect and drive a source code build stack to reach well-known targets.

Usage:
  build [options] init <toolid> [<setting>...]
  build [options] <target>...
  build --help

Options:
  -C <path>, --directory <path>  set working directory
  -m <str>, --message <str>      set commit message on release
  -f <path>, --file <path>       set build manifest path (overrides -C)
  -p <id>, --profile <id>        set build profile
  -v, --verbose                  trace execution
  -h, --help                     display full help text
  --no-color                     disable colored output

Where <target> is one of:
  * get:<id>             install requirement(s)
  * clean                delete generated objects
  * compile              generate target objects from source code
  * test                 run unit tests
  * package[:<id>]       bundle target objects with metadata [in the identified format]
  * publish[:<id>]       publish packages [to the identified repository]
  * [un]install[:<id>]   [un]deploy target objects [onto the identified inventory]
  * release[:<id>] [-m]  bump project version, commit and tag

Examples:
  To compile the project in subdir foo and install it:
    $ build -C foo/ clean compile install
  To run unit tests, clean-up and release:
    $ build test clean release:patch
  Clean-up, compile, package and publish:
    $ build clean compile package publish

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

	def __init__(self, customization = None, profileid = None, path = None):
		self.customization = customization or {}
		self.profileid = profileid
		if path:
			path = utils.Path(path)
			if os.path.isdir(path):
				dirname = path
				self.filename = None
			elif os.path.isfile(path):
				dirname, self.filename = os.path.split(path)
			else:
				raise Error(path, "invalid path")
			if dirname:
				utils.chdir(dirname)
		else:
			self.filename = None
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
			raise Error(
				"/".join(map(lambda m: m["name"], manifests)),
				"multiple build stacks detected, use -f to select a manifest")
		else:
			self.manifest, = manifests
		for key in ("name", "filenames"):
			if not key in self.manifest:
				raise Error(key, "missing required manifest property")
		self.targets = Targets()
		utils.trace("using '%s' build stack" % self.manifest["name"])

	def _check_call(self, args, _cache = {}):
		key = args[0]
		if not key in _cache:
			# fetch general customization, if any:
			_cache[key] = self.customization.get("all", {}).get(key, {})
			# fetch profile customization, if any:
			if self.profileid:
				_cache[key].update(self.customization.get(self.profileid, {}).get(key, {}))
		tmp = list(args)
		tmp[0] = os.path.expanduser(_cache[key].get("path", key))
		argslist =\
			_cache[key].get("before", [])\
			+ [tmp + _cache[key].get("append", [])]\
			+ _cache[key].get("after", [])
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
				self._check_call(("git", "clean", "--force", "-d", "-x")) # "Danger, Will Robinson!"
			elif os.path.exists(".hg"):
				self._check_call(("hg", "purge", "--config", "extensions.purge="))
			else:
				raise Error("unknown VCS, cannot remove untracked files") # NOTE: add svn-cleanup
		elif callable(handler):
			for res in (handler)(
				filename = self.filename,
				targets = self.targets,
				**kwargs):
				if isinstance(res, (list, tuple)):
					{
						"@trace": utils.trace,
						"@remove": utils.remove,
					}.get(res[0], lambda *args: self._check_call([res[0]] + list(args)))(*res[1:])
				elif res == "flush":
					assert canflush, "%s: cannot flush from this target" % key
					self.flush()
				else: # res is an error object
					raise Error(self.manifest["name"], name, res)
		else:
			assert False, "%s: invalid target handler" % handler

	def get(self, requirementid):
		self._handle_target(
			"get",
			default = "fail",
			requirementid = requirementid)

	def clean(self):
		self._handle_target("clean")

	def compile(self):
		self._handle_target("compile")

	def test(self):
		self._handle_target("test")

	def package(self, formatid = None):
		self._handle_target(
			"package",
			formatid = formatid)

	def publish(self, repositoryid = None):
		self._handle_target(
			"publish",
			repositoryid = repositoryid)

	def install(self, inventoryid = None, uninstall = False):
		self._handle_target(
			"install",
			inventoryid = inventoryid,
			uninstall = uninstall)

	def release(self, typeid, message):
		self._handle_target(
			"release",
			typeid = typeid,
			message = message)

	def flush(self):
		if self.targets:
			self._handle_target("flush", canflush = False, default = "fail")
		if self.targets:
			raise Error(self.manifest["name"], "lingering unhandled target(s) -- please report this bug")

def init(toolid, settings):
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
		suffix = "-- see 'build init help'"
		if not toolid in tools:
			raise Error(toolid, "unknown tool", suffix)
		path = os.path.expanduser(tools[toolid]["path"])
		if settings:
			settings = dict(tools[toolid]["defaults"], **(dict(map(lambda item: item.split("="), settings))))
		else:
			settings = {}
		if not os.path.exists(path) or settings.get("overwrite", "no") == "yes":
			try:
				text = textwrap.dedent(tools[toolid]["template"]).lstrip() % settings
			except KeyError as exc:
				raise Error(" ".join(exc.args), "missing required variable" + suffix)
			with open(path, "w") as fp:
				fp.write(text)
			utils.trace("%s: template instantiated" % path)
		else:
			raise Error(path, "file already exists, set overwrite=yes to force")

def main(*args):
	opts = docopt.docopt(
		doc = __doc__,
		argv = args or None)
	try:
		if opts["--no-color"]:
			utils.disable_colors()
		if opts["--verbose"]:
			utils.enable_tracing()
		if opts["init"]:
			init(
				toolid = opts["<toolid>"],
				settings = opts["<setting>"])
		else:
			bs = BuildStack(
				customization = utils.parse_file("~/build.json", default = None),
				profileid = opts["--profile"],
				path = opts["--file"] or opts["--directory"])
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
