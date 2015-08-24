# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Detect and drive a source code build stack to reach well-known targets.

Usage:
  build [options] setup TOOLID [SETTING...]
  build [options] TARGET...
  build --help

Options:
  -C PATH, --directory PATH  set working directory
  -f PATH, --file PATH       set build manifest path (overrides -C)
  -p ID, --profile ID        set build profile
  -v, --verbose              trace execution
  -h, --help                 display full help text
  --no-color                 disable colored output

Where TARGET is one of:
  * get[:ID]          install requirement(s)
  * clean             delete generated files
  * compile           generate target objects from source code
  * run[:ID]          execute entry point(s)
  * test              run unit tests
  * package[:ID]      bundle target objects with metadata [in the identified format]
  * publish[:ID]      publish packages [to the identified repository]
  * [un]install[:ID]  [un]deploy target objects [onto the identified inventory]
  * release:ID        bump source code version, commit and tag

Example:
  $ build clean compile test

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

import docopt, utils # 3rd-party

MANIFESTS = reduce(
	lambda _tuple, _dict: _tuple + (_dict,),
	(__import__(name, globals()).MANIFEST for name in (
		"ansible",
		"ant",
		"autotools",
		"builtin",
		"cargo",
		"gradle",
		"grunt",
		"maven",
		"npm",
		"rake",
		"setuptools",
		"vagrant")),
	())


class Error(utils.Error): pass


class Vcs(object):
	"tiny VCS abstraction handling commit(), purge() and tag()"

	def __init__(self):
		for key in (".hg", ".git", ".svn"):
			if os.path.exists(key):
				self.key = key

	def commit(self, message):
		return {
			".git": ("git", "commit", "-am", message),
		}.get(self.key, "unsupported operation")

	def purge(self):
		"Danger, Will Robinson! -- you may loose data"
		return {
			".git": ("git", "clean", "--force", "-d", "-x"),
			".hg": ("hg", "purge", "--config", "extensions.purge="),
		}.get(self.key, "unsupported operation")

	def tag(self, name):
		return {
			".git": ("git", "tag", name),
		}.get(self.key, "unsupported operation")


class Version(object):
	"immutable N(.N)* version object"

	def __init__(self, *number):
		self.number = number

	def __eq__(self, other):
		return self.number == other.number

	def __str__(self):
		return ".".join(map(str, self.number))

	def parse_stdout(self, *args):
		stdout = utils.check_output(*args)
		self.number = map(int, stdout.split("."))

	def bump(self, partid):
		"return a new bumped version object"
		number = [i for i in self.number]
		if partid == "major":
			i = 0
		elif partid == "minor":
			i = 1
		elif partid == "patch":
			i = max(2, len(number) - 1)
		else:
			try:
				i = int(partid)
			except ValueError:
				raise Error(partid, "unexpected partid")
		if i >= len(number):
			number += [0] * (i - len(number) + 1)
		number[i] += 1
		return Version(*number)


class Target(object):

	def __init__(self, name, **kwargs):
		self.name = name
		self.kwargs = kwargs

	def __str__(self):
		return "%s %s" % (self.name, " ".join("%s=%s" % (k, v) for k, v in self.kwargs.items()))

	def __eq__(self, other): # FIXME: deprecated this?
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

	def __init__(self, preferences = None, profileid = None, manifests = None, path = None):
		# resolve preferences:
		if preferences:
			self.preferences = preferences.get("all", {})
			if profileid:
				self.preferences.update(preferences.get(profileid, {}))
		else:
			self.preferences = {}
		# resolve base directory:
		if path:
			path = utils.Path(path)
			if os.path.isdir(path):
				dirname = path
				self.filename = None
			else:
				dirname, self.filename = os.path.split(path)
			if dirname:
				utils.chdir(dirname)
		else:
			self.filename = None
		# resolve manifest:
		cnt = 0
		for manifest in manifests:
			for pattern in manifest["filenames"]:
				if self.filename:
					if fnmatch.fnmatch(self.filename, pattern):
						self.manifest = manifest
						cnt += 1
				else:
					filenames = glob.glob(pattern)
					if filenames:
						self.filename = filenames[0] # pick first match
						self.manifest = manifest
						cnt += 1
		if not cnt:
			raise Error("no supported build stack detected")
		elif cnt > 1:
			raise Error("multiple build stacks detected, use -f to select a manifest")
		utils.trace("using %s build stack" % self.manifest["name"])
		self.targets = Targets()
		self.vcs = Vcs()

	def _check_call(self, args):
		prefs = self.preferences.get(args[0], {})
		tmp = list(args)
		tmp[0] = prefs.get("path", args[0]) # FIXME: this is ugly
		argslist = prefs.get("before", []) + [tmp + prefs.get("append", [])] + prefs.get("after", [])
		for args in argslist:
			args[0] = utils.Path(args[0])
			utils.check_call(*args)

	def _handle_target(self, name, canflush = True, default = "stack", **kwargs):
		"generic target handler: call the custom handler if it exists, or fallback on default"
		handler = self.manifest.get("on_%s" % name, default)
		if handler is None:
			raise Error(self.manifest["name"], name, "unsupported target")
		elif handler == "stack": # stack target and let the on_flush handler deal with it
			self.targets.append(name, **kwargs)
		elif callable(handler):
			for res in (handler)(
				filename = self.filename,
				targets = self.targets,
				**kwargs):
				if isinstance(res, (list, tuple)):
					if res[0] == "@try":
						try:
							self._check_call(res[1:])
						except:
							utils.trace("command failure ignored")
					elif res[0] == "@tag":
						self._check_call(self.vcs.tag(*res[1:]))
					elif res[0] == "@flush":
						assert canflush, "%s: cannot flush from this target" % key
						self.flush()
					elif res[0] == "@trace":
						utils.trace(*res[1:])
					elif res[0] == "@purge":
						self._check_call(self.vcs.purge())
					elif res[0] == "@commit":
						self._check_call(self.vcs.commit(*res[1:]))
					elif res[0] == "@remove":
						utils.remove(*res[1:])
					else:
						self._check_call(res)
				else: # res is an error object
					raise Error(self.manifest["name"], name, res)
		else:
			raise AssertionError("invalid target handler")

	def get(self, requirementid = None):
		self._handle_target(
			"get",
			default = None,
			requirementid = requirementid)

	def clean(self):
		self._handle_target("clean")

	def compile(self):
		self._handle_target("compile")

	def run(self, entrypointid = None):
		self._handle_target(
			"run",
			entrypointid = entrypointid)

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

	def release(self, partid):
		self._handle_target(
			"release",
			partid = partid,
			version = Version())

	def flush(self):
		if self.targets:
			self._handle_target("flush", canflush = False, default = None)
		assert not self.targets, "lingering target(s) -- please report this bug"


def setup(toolid, settings, manifests):
	"render a tool configuration template"
	tools = {}
	for manifest in manifests:
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
		suffix = "-- see 'build setup help'"
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
		if opts["setup"]:
			setup(
				toolid = opts["TOOLID"],
				settings = opts["SETTING"],
				manifests = MANIFESTS)
		else:
			bs = BuildStack(
				preferences = utils.unmarshall("~/buildstack.json"),
				profileid = opts["--profile"],
				manifests = MANIFESTS,
				path = opts["--file"] or opts["--directory"])
			for target in opts["TARGET"]:
				if target.startswith("get"):
					bs.get(requirementid = target.partition(":")[2])
				elif target == "clean":
					bs.clean()
				elif target == "compile":
					bs.compile()
				elif target.startswith("run"):
					bs.run(entrypointid = target.partition(":")[2])
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
					bs.release(partid = target.partition(":")[2])
				else:
					raise Error(target, "unknown target")
				bs.flush()
	except utils.Error as exc:
		raise SystemExit(utils.red(exc))
