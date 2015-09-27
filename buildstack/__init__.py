# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"""
Detect and drive any build stack to reach well-known targets.

Usage:
  buildstack [options] setup TOOLID [SETTING...]
  buildstack [options] TARGETS...
  buildstack --help

Options:
  -C PATH, --directory PATH  set working directory
  -f PATH, --file PATH       set build manifest path (overrides -C)
  -m STR, --message STR      set commit message
  -p ID, --profile ID        set build profile
  -v, --verbose              trace execution
  -h, --help                 display full help text
  --no-color                 disable colored output

TARGET:
  * get[:ID]          install requirement(s)
  * clean             delete generated files
  * compile           generate target objects from source code
  * run[:ID]          execute entry point(s)
  * test              run unit tests
  * package[:ID]      bundle target objects with metadata [in the identified format]
  * publish[:ID]      publish packages [to the identified repository]
  * [un]install[:ID]  [un]deploy target objects [onto the identified inventory]
  * release:ID [-m]   bump source code version, commit, tag and push

Lifecycles:
  * get
  * clean
  * run     > compile
  * release > test > compile
  * install > package > test > compile
  * publish > package > test > compile

Example:
  $ buildstack clean test

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

import docopt, fckit # 3rd-party

MANIFESTS = tuple(dict({"name": name}, **__import__(name, globals()).MANIFEST) for name in (
	"ansible",
	"ant",
	"autotools",
	"builtin",
	"cargo",
	"cmake",
	"gradle",
	"grunt",
	"gulp",
	"maven",
	"ninja",
	"npm",
	"rake",
	"scons",
	"setuptools",
	"stack",
	"tup",
	"vagrant"))

class Error(fckit.Error): pass

class Vcs(object):

	def __init__(self):
		for key in (".hg", ".git", ".svn"):
			if os.path.exists(key):
				self.attr = {
					".git": {
						"commit": lambda message: ("git", "commit", "-am", message),
						"purge": lambda: ("git", "clean", "--force", "-d", "-x"),
						"push": lambda: ("git", "push", "--follow-tags"), # work with annotated tags
						"tag": lambda name: ("git", "tag", "-a", "-m", "release", name),
					},
					".svn": {},
					".hg": {
						"commit": lambda message: ("hg", "commit", "-m", message),
						"purge": lambda: ("hg", "purge", "--config", "extensions.purge="),
						"push": lambda: ("hg", "push"),
						"tag": lambda name: ("hg", "tag", name),
					},
				}[key]

	def __getattr__(self, key):
		try:
			return self.attr[key]
		except KeyError:
			raise Error("unsupported operation")

class Version(object):
	"immutable N(.N)* version object"

	@staticmethod
	def parse_stdout(*args):
		stdout = fckit.check_output(*args)
		number = map(int, stdout.split("."))
		return Version(*number)

	def __init__(self, *number):
		self.number = number

	def __str__(self):
		return ".".join(map(str, self.number))

	def bump(self, partid):
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
				raise Error(partid, "expected (major|minor|patch) or index")
		if i >= len(number):
			number += [0] * (i - len(number) + 1)
		for j in range(0, len(number)):
			if j < i:
				continue
			elif j == i:
				number[j] += 1
			else:
				number[j] = 0
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
		tgt = Target(name, **kwargs)
		if not len(self) or self[-1] != tgt: # do not push twice the same target
			super(Targets, self).append(tgt)

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
			path = fckit.Path(path)
			if os.path.isdir(path):
				dirname = path
				self.filename = None
			else:
				dirname, self.filename = os.path.split(path)
			if dirname:
				fckit.chdir(dirname)
		else:
			self.filename = None
		# resolve manifest:
		if self.filename:
			candidates = {manifest["name"]: (manifest, self.filename)
				for manifest in manifests
					for pattern in manifest["filenames"]
						if fnmatch.fnmatch(self.filename, pattern)}
		else:
			candidates = {manifest["name"]: (manifest, filename)
				for manifest in manifests
					for pattern in reversed(manifest["filenames"])
						for filename in glob.glob(pattern)[:1]}
		if not candidates:
			raise Error("no known manifest found")
		elif len(candidates) > 1:
			raise Error(
				[filename for manifest, filename in candidates.values()],
				"multiple candidate manifests found, use -f to select a manifest")
		self.manifest, self.filename = candidates.values()[0]
		fckit.trace("using %s build stack" % self.manifest["name"])
		self.targets = Targets()
		self.vcs = Vcs()

	def _check_call(self, args):
		prefs = self.preferences.get(args[0], {})
		args = list(args)
		args[0] = prefs.get("path", args[0])
		argslist = prefs.get("before", []) + [args + prefs.get("append", [])] + prefs.get("after", [])
		for args in argslist:
			args[0] = fckit.Path(args[0])
			fckit.check_call(*args)

	def _handle_target(self, name, default = "stack", **kwargs):
		"generic target handler: call the custom handler if it exists, or fallback on default"
		fckit.trace(">>", "[", name, "]")
		handler = self.manifest.get("on_%s" % name, default)
		if handler is Exception:
			raise Error(self.manifest["name"], name, "unsupported target")
		elif handler is None:
			pass
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
							fckit.trace("command failure ignored")
					elif res[0] == "@tag":
						self._check_call(self.vcs.tag(*res[1:]))
					elif res[0] == "@push":
						self._check_call(self.vcs.push())
					elif res[0] == "@flush":
						assert name != "flush", "infinite recursion detected"
						self.flush()
					elif res[0] == "@trace":
						fckit.trace(*res[1:])
					elif res[0] == "@purge":
						self._check_call(self.vcs.purge())
					elif res[0] == "@commit":
						self._check_call(self.vcs.commit(*res[1:]))
					elif res[0] == "@remove":
						fckit.remove(*res[1:])
					else:
						self._check_call(res)
				else: # res is an error object
					raise Error(self.manifest["name"], name, res)
		else:
			raise AssertionError("invalid target handler")
		fckit.trace("<<", "[", name, "]")

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
		self.compile()
		self._handle_target(
			"run",
			entrypointid = entrypointid)

	def test(self):
		self.compile()
		self._handle_target("test")

	def package(self, formatid = None):
		self.test()
		self._handle_target(
			"package",
			formatid = formatid)

	def publish(self, repositoryid = None):
		self.package()
		self._handle_target(
			"publish",
			repositoryid = repositoryid)

	def install(self, inventoryid = None, uninstall = False):
		self.package()
		self._handle_target(
			"install",
			inventoryid = inventoryid,
			uninstall = uninstall)

	def release(self, partid, message = None):
		self.test()
		self._handle_target(
			"release",
			partid = partid,
			message = message,
			Version = Version)

	def flush(self):
		if self.targets:
			self._handle_target("flush", default = None)
		assert not self.targets, "lingering target(s), please report this bug!"

def setup(toolid, settings, manifests):
	"render a tool configuration template"
	tools = {k: v for m in manifests for k, v in m.get("tools", {}).items()}
	if toolid == "help":
		name_width = max(map(len, tools))
		path_width = max(map(lambda key: len(tools[key]["path"]), tools))
		for key in tools:
			required = ", ".join(tools[key]["required_vars"])
			optional = ", ".join("%s=%s" % (k, v) for k,v in tools[key]["defaults"].items())
			print\
				fckit.magenta(key.rjust(name_width)),\
				tools[key]["path"].center(path_width),\
				required,\
				("[%s]" % optional) if optional else ""
	else:
		suffix = ", see 'build setup help'"
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
			fckit.trace("%s: template instantiated" % path)
		else:
			raise Error(path, "file already exists, set overwrite=yes to force")

def main(args = None):
	opts = docopt.docopt(
		doc = __doc__,
		argv = args)
	try:
		if opts["--no-color"]:
			fckit.disable_colors()
		if opts["--verbose"]:
			fckit.enable_tracing()
		if opts["setup"]:
			setup(
				toolid = opts["TOOLID"],
				settings = opts["SETTING"],
				manifests = MANIFESTS)
		else:
			bs = BuildStack(
				preferences = fckit.unmarshall("~/buildstack.json"),
				profileid = opts["--profile"],
				manifests = MANIFESTS,
				path = opts["--file"] or opts["--directory"])
			switch = {
				"get": lambda value: bs.get(requirementid = value),
				"clean": lambda _: bs.clean(),
				"compile": lambda _: bs.compile(),
				"run": lambda value: bs.run(entrypointid = value),
				"test": lambda _: bs.test(),
				"package": lambda value: bs.package(formatid = value),
				"publish": lambda value: bs.publish(repositoryid = value),
				"install": lambda value: bs.install(inventoryid = value),
				"uninstall": lambda value: bs.install(inventoryid = value, uninstall = True),
				"release": lambda value: bs.release(partid = value, message = opts["--message"])
			}
			for target in opts["TARGETS"]:
				key, _, value = target.partition(":")
				if key in switch:
					switch[key](value)
				else:
					raise Error(target, "unknown target")
			bs.flush()
	except fckit.Error as exc:
		raise SystemExit(fckit.red(exc))
