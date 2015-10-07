
**BuildStack** is a wrapper around build tools and their ecosystem:
its goal is to abstract the build process of any source code repository
by driving the underlying build stack through [well-known targets](#glossary).
Focus on the big picture and let **BuildStack** handle the details.

The following [well-known targets](#glossary) are supported:
  * `get:ID` install requirements
  * `clean` delete build byproducts
  * `compile` compile code
  * `run` run project
  * `test` run unit tests
  * `release:ID` bump source code version, commit, tag and push
  * `package[:ID]` package code [in the specified format]
  * `publish[:ID]` publish package(s) [to the specified repository]
  * `install[:ID]` install package(s) [on the specified inventory]
  * `uninstall[:ID]`  uninstall package(s) [from specified inventory]

The following [lifecycles](#glossary) are supported:
  * **`get`**
  * **`clean`**
  * **`run`** > `compile`
  * **`test`** > `compile`
  * **`release`** > `test` > `compile`
  * **`install`** > `package` > `test` > `compile`
  * **`publish`** > `package` > `test` > `compile`
  * **`uninstall`**

| Stack | Setup | Get | Clean | Run | Test | Rel. | Ins. | Pub. | Unins. |
|-------|-------|-----|-------|-----|------|------|------|------|--------|
| [Setuptools][2] | ✚ | ✔+ | ✔ | ✔ | ✔+ | ✔ | ✔ | ✔+ | ✔ |
| [Autotools][1] | ✗ | ✗ | ✔+ | ✗ | ✔ | ✗ | ✔ | ✗ | ✔ |
| [Ansible][5] | — | ✔+ | ✔ | ✔ | ✔ | — | — | — | — |
| [Maven][3] | ✚ | ✔ | ✔ | ✗ | ✔ | ✗ | ✔ | ✔ | ✔ |
| [Cargo][4] | ✚ | ✔ | ✔ | ✔ | ✔ | ✗ | ✗ | ✔ | ✗ |

  * ✚ Not natively supported but implemented by buildstack
  * ✔+ Partial native support, completed by buildstack
  * ✘ Not natively supported
  * — Undefined

Why, Oh Why?
------------

[SwQA engineers][9], [Build & Release engineers][10] and [developers][11] are all dealing with the same problem:
how to quickly build and work with a project using a build stack they are not familiar with?
By using **BuildStack**, check out any repository and reach your build targets.
No question asked and no need to lookup documentation.

	$ git pull $HOST/$FOO.git
	$ build -C $FOO clean test # automatically triggers 'compile'


Extra Features
--------------

  * [Lifecycles](#glossary) support.
  * Instantiate tool configuration templates, see `build setup help`.
  * [Autotools][1]:
    * better `clean` (remove lingering generated files)
  * [Setuptools][2]:
    * better `clean` (remove lingering generated files)
    * support the `run` target: fetch and run entry points from the manifest
    * support the `release` target
    * use `build package:pkg` to build native OS/X packages (on an OS/X platform.)
    * use `build package:deb` to build debian packages (on a debian platform.)
      Install the following tools beforehand:

			$ sudo pip install make-deb
			$ sudo add-apt-repository ppa:dh-virtualenv/daily
			$ sudo apt-get update
			$ sudo apt-get install debhelper dh-virtualenv

    * on testing,
      if `nose2.cfg` is present and setup.py does not use it,
      the original setup.py will be backed up and a new one will be generated to call nose2.


Pre-requisites
--------------

As **BuildStack** is not bundled with any build tool, provision the machine appropriately beforehand.


Installation
------------

	$ pip install --user buildstack

To uninstall:

	$ pip uninstall buildstack


Configuration
-------------

Create the file `~/buildstack.json` to customize each command executed by `build`:

  * `before`: run commands before
  * `after`: run commands after
  * `append`: append extra arguments to the command
  * `path`: set command path (e.g. on user-wide installation)

Customizations can be grouped into "profiles", use the `--profile` switch on the command line to select one.

For instance to provision an Ansible inventory as root with a password:

	{
		[…]
		"as-root": {
			"ansible-playbook": {
				"append": ["--user", "root", "--ask-pass"]
			}
		}
		[…]
	}

This would be invoked with the option `--profile as-root`.

You may also use the special profile `all` which is always applied.


Development Guide
-----------------

**Buildstack** can be extended easily to support additional tools.

### MODULE CREATION

Create a python module in the `buildstack/` directory,
and add its name to the list initializing `MANIFESTS` in `__init__.py`.
You might use the following template as bootstrap.
The module must define a `MANIFEST` global variable to be loaded;
this variable is a dictionary declaring the module properties and handlers.

	#def on_get(filename, targets, requirementid):
	#def on_clean(filename, targets):
	#def on_compile(filename, targets):
	#def on_run(filename, targets, entrypointid):
	#def on_test(filename, targets):
	#def on_release(filename, targets, partid, message, Version):
	#def on_package(filename, targets, formatid):
	#def on_publish(filename, targets, repositoryid):
	#def on_install(filename, targets):
	#def on_uninstall(filename, targets):
	#def on_flush(filename, targets):
	MANIFEST = {
		"filenames": [], # list of patterns matching supported build manifest filenames
		#"name": # build stack custom name, defaults to module name otherwise
		#"on_get": Exception | None | on_get,
		#"on_clean": Exception | None | on_clean,
		#"on_compile": Exception | None | on_compile,
		#"on_run": Exception | None | on_run,
		#"on_test": Exception | None | on_test,
		#"on_release": Exception | None | on_release,
		#"on_package": Exception | None | on_package,
		#"on_publish": Exception | None | on_publish,
		#"on_install": Exception | None | on_install,
		#"on_uninstall": Exception | None | on_uninstall,
		#"on_flush": Exception | None | on_flush,
		#"tools": {}
	}

### TARGET STACK

For all handlers, except `on_get()` and `on_flush()`, the default behavior is to stack the target onto the `targets` list.
The handler `on_flush()` is automatically called last to unstack and process the targets or
it can also be called manually from any handler with the `@flush` command (detailed below.)
The `targets` list must be empty when `on_flush()` terminates or the plugin is considered faulty.
The rationale behind the usage of a stack is that most build tools are able to handle multiple
targets at the same time (e.g. make clean all) and calling them independently is less efficient.
However, what can be stacked or not varies for each build tool: therefore, when developping a plugin,
use target handlers to perform a task that cannot be stacked. Also, when using a handler,
remember to flush the current stack at the appropriate point (usually at the beginning, before anything else.)

### HANDLERS

When setting a handler in the `MANIFEST`, there are 3 options:
  * A value of `Exception` indicates the handler is not supported and will raise an error at runtime.
  * A value of `None` indicates that there is nothing to do for this handler.
  * A generator callback with the proper signature.

A generator callback can yield either:
  * a command, i.e. a sequence of strings, e.g. `yield "echo", "hello"`
  * any single object -- considered as an error object and raising `build.Error()`

If a command image name (i.e. its first element) starts with "@",
it is considered to be a builtin function, e.g. `yield "@trace", "hello"`.

The following builtins are available:
  * `try(*args)` — exec args, resume on exception
  * `tag` — triggers a VCS tag
  * `push` — triggers a VCS push
  * `flush([reason])` — triggers `on_flush()`
  * `trace(*strings)` — trace execution
  * `purge()` — triggers a VCS purge, i.e. delete all untracked files
  * `commit([message])` — triggers a VCS commit
  * `remove(path[, reason])` — remove file or directory

### RELEASE TARGET

Few build stacks are able to handle a `release` target natively,
**BuildStack** therefore provides some support to work around this issue given that you can:
  1. fetch the current project version, either:
     * by using the build tool to extract project attributes (e.g. `python setup.py --version`)
     * or by parsing the build manifest directly
  2. write back the new version into the build manifest

To calculate the new version, **BuildStack** passes the `Version` class to your release handler.
Of course, you can ignore this argument if you have another mean to do version calculation.
  * `Version.parse_stdout(*args)` — return version instance from the command output (it should match `N(.N)*`)
  * `version.bump(partid)` — return bumped version, where partid is (major|minor|patch) or an index.

### TESTING

You can use buildstack to test itself without installing it, given its dependencies are present:

	$ python -m buildstack test

Otherwise:

	$ python setup.py test

To test concrete build stacks, build the provided [Docker][12] files, e.g.:

	$ sudo docker build -f test_autotools.Dockerfile .


Build Engineering 101
---------------------

<a id="glossary"></a>
### GLOSSARY

  * **Build Target**:
    Abstract or concrete state to reach.
    Concrete build targets are generally platform objects such as files;
    Abstract build targets (aka [phony targets][13] in Make jargon)  are varying depending on the tool, but well-know targets should be supported.
  * **Dependency Graph**:
    Graph specifying dependencies between concrete build targets.
    For instance, the source files from which an object file is compiled.
  * **Well-known Build Target**:
    Abstract build target supported by most build tools: clean, compile, test, package, install, publish.
  * **Lifecycle**:
    Logical sequence of build target such that invoking one implies its predecessors.
    See [Maven Lifecycles][7] for details.

### BUILD STACKS TAXONOMY

**NOTICE! The following classification is my personal standpoint.**

Build stacks can be divided into 5 types:

  * Type 1: **Build library** — Collection of build functions
  * Type 2: **Build framework** — Dependency graph manager + Type 1 features
  * Type 3: **Build DSL** (over a type 2)
  * Type 4: **Build Programmable Configuration**
  * Type 5: **Build Configuration**, the current state of the art (back to .ini files!)

For types 1 and 2,
the build manifest is actually a program.
It is generally written in the language for which the build stack was designed, but not necessarily.
This means it has to be created and maintained by developers who must have a solid knowledge of build engineering.
If this not the case, the result is an overly custom build system that is neither learnable nor maintainable.
Enforcing the usage of a dependency graph, which is the core of any proper build system, can only be done from types 2.
For this reason, types 1 are to be avoided at all costs for the sanity of the technical teams.

Avoiding having developers design the build system can only be done from types 3.
The canonical example of types 3 is [Make][8].
The build manifest can be written by build engineers in a DSL allowing to specify the dependency graph and how to walk it.
DSL are far more safe, but they can still be misused, so types 3 are not bullet-proof.

Types 4 and 5 enforce configuration and convention over programming.
The canonical example of types 5 is [Maven][3].
Such a build stack knows what and how to build, assuming your provide the bootstrap information.
For non-exotic projects you should have very little to provide to get a working build stack:
  * a project name
  * a version
  * a type (library or executable)
  * an entry point for an executable.

### CHOOSING A BUILD STACK

From a development standpoint, how to choose a stack? it's easy:
  1. If there is a **standard build stack**, then however bad it is, use it, and request improvements
  2. If there is no standard build stack, then pick the **highest type** available according to the above taxonomy.

Keep in mind that anything below type 4 will slow the project at some point:
  * either because it will break easily as soon as the source project is slightly reorganized
  * or, because of initial shortcuts, it cannot meet new needs without major rework
  * or because it is too difficult to use
  * or because its learning curve is too steep for newcomers
  * or because of a combination of any of the above reasons.

### CLASSIFICATION OF CONCRETE BUILD STACKS

| Type | Name | Build Manifest Format |
|------|------|-----------------------|
| 5 | [Maven][3] | XML |
| 5 | [Cargo][4] | ini |
| 4 | [Setuptools][2] | Python Call |
| 4 | [Autotools][1] | M4 Macros |
| 3 | [Make][8] | Make Rules |

<!-- REFERENCES -->
[1]: https://www.sourceware.org/autobook
[2]: https://packaging.python.org
[3]: https://maven.apache.org
[4]: http://doc.crates.io
[5]: http://docs.ansible.com/ansible/index.html
[6]: https://en.wikipedia.org/wiki/Software_build
[7]: https://maven.apache.org/ref/3.3.3/maven-core/lifecycles.html
[8]: https://www.gnu.org/software/make/
[9]: https://en.wikipedia.org/wiki/Software_quality_assurance
[10]: https://en.wikipedia.org/wiki/Release_engineering
[11]: https://en.wikipedia.org/wiki/Software_developer
[12]: https://www.docker.com
[13]: https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html

