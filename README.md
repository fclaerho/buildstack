
*NOTICE!
This tool is stable for the use cases it covers but it does not cover all major use cases yet.
So far you can build [autotools][1], [setuptools][2], [maven][3], [cargo][4] and [ansible][5]-based projects.*

**BuildStack** is a wrapper around build tools and their ecosystem:
its goal is to abstract the build process of any source code repository
by driving the underlying build stack through _well-known targets_.
Focus on the big picture and let **BuildStack** handle the details.

The following [well-known targets][6] are supported:
  * `get:ID` install requirements
  * `clean` delete build byproducts
  * `compile` compile code
  * `run` run project
  * `test` run unit tests
  * `package[:ID]` package code [in the specified format]
  * `publish[:ID]` publish package [to the specified repository]
  * `[un]install[:ID]` [un]install locally [or [un]provision inventory]
  * `release:ID [-m]` bump source code version, commit, tag and push

The following [lifecycles][7] are supported:
  * **`get`**
  * **`clean`**
  * **`run`** > `compile`
  * **`release`** > `test` > `compile`
  * **`install`** > `package` > `test` > `compile`
  * **`publish`** > `package` > `test` > `compile`


Why, Oh Why?
------------

[SwQA engineers][9], [Build & Release engineers][10] and [developers][11] are all dealing with the same problem:
how to quickly build and use a project using a build stack they are not familiar with?
By using **BuildStack**, check out any repository and reach your build targets.
No question asked and no need to lookup documentation.

	$ git pull $HOST/$FOO.git
	$ build -C $FOO clean test # automatically triggers 'compile'


Extra Features
--------------

  * [Lifecycles][7] support.
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

or, if the PyPI repository is not available:

	$ pip install --user git+https://github.com/fclaerho/buildstack.git

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

### Module Creation ###

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
	#def on_package(filename, targets, formatid):
	#def on_publish(filename, targets, repositoryid):
	#def on_install(filename, targets, uninstall):
	#def on_release(filename, targets, partid, message, Version):
	#def on_flush(filename, targets):
	MANIFEST = {
		"filenames": [], # list of patterns matching supported build manifest filenames
		#"name": # build stack custom name, defaults to module name otherwise
		#"on_get": Exception | None | on_get,
		#"on_clean": Exception | None | on_clean,
		#"on_compile": Exception | None | on_compile,
		#"on_run": Exception | None | on_run,
		#"on_test": Exception | None | on_test,
		#"on_package": Exception | None | on_package,
		#"on_publish": Exception | None | on_publish,
		#"on_install": Exception | None | on_install,
		#"on_release": Exception | None | on_release,
		#"on_flush": Exception | None | on_flush,
		#"tools": {}
	}

### Target Stack ###

For all handlers, except `on_flush()`, the default behavior is to stack the target onto the `targets` list.
The handler `on_flush()` is automatically called _last_ to unstack and process the targets or
it can also be called manually from any handler with the `@flush` command (detailed below.)
The `targets` list _must_ be empty when `on_flush()` terminates or the plugin is considered faulty.
The rationale behind the usage of a stack is that most build tools are able to handle multiple
targets at the same time (e.g. make clean all) and calling them independently is less efficient.
However, what can be stacked or not varies for each build tool: therefore, when developping a plugin,
use target handlers to perform a task that cannot be stacked. Also, when using a handler,
remember to flush the current stack at the appropriate point (usually at the beginning, before anything else.)

### Handlers ###

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

### Release Target ###

Few build stacks are able to handle a `release` target natively,
**BuildStack** therefore provides some support to work around this issue given that you can:
  1. fetch the current project version, either:
     * by using the build tool to extract project attributes (e.g. `python setup.py --version`)
     * or by parsing the build manifest directly
  2. write back the new version into the build manifest

To calculate the new version, **BuildStack** passes the `Version` class to your release handler.
Of course, you can ignore this argument if you have another mean to do version calculation.
  * `Version.parse_stdout(*args)` — return version instance from the command output (it should match N(.N)*)
  * `version.bump(partid)` — return bumped version, where partid is (major|minor|patch) or an index.

### Testing ###

You can use buildstack to test itself without installing it, given its dependencies are present:

	$ python -m buildstack test

Otherwise:

	$ python setup.py test

To test concrete build stacks, build the provided [Docker](https://www.docker.com) files, e.g.:

	$ sudo docker build -f test_autotools.Dockerfile .


Build Stack Taxonomy
--------------------

There's no reference for the following statements because this is a personal standpoint.

### Types of Build Stack ###

Build stacks can be divided into 4 types:

  * Type 1: **Build library** — Collection of build functions
  * Type 2: **Build framework** — Dependency graph manager + Type 1 features
  * Type 3: **Build DSL** (over a type 2)
  * Type 4: **Build Configuration**, the current state of the art.

For types 1 and 2,
the build manifest is actually a program.
It is generally written in the language for which the build stack was designed, but not necessarily.
This means it has to be created and maintained by developers who must have a solid knowledge of build engineering.
If this not the case, the result is an overly custom build system that is neither learnable nor maintainable.
Enforcing the usage of a dependency graph, which is the core of any proper build system, can only be done from types 2.
For this reason, types 1 are to be avoided at all costs for the sanity of the technical teams.

Avoiding having developers design the build system can only be done from types 3.
The canonical example of types 3 is Make.
The build manifest can be written by build engineers in a DSL allowing to specify the dependency graph and how to walk it.
However, even types 3 do not guarantee a maintainable build system, as it might still be easy to create custom mechanisms.

The canonical example of types 4 is Maven.
Types 4 enforce configuration and convention over programming.
A type 4 knows when, what and how to build, assuming your provide the bootstrap information.
For some typical projects you might have very little to provide: a project name, version and authors.

### Choosing a Build Stack ###

How to choose a stack? it's easy:
  1. If there is a **standard build stack**, then however bad it is, use it, and request improvements
  2. If there is no standard build stack, then pick the **highest type** available according to the above taxonomy.

Keep in mind that anything below type 4 will slow the project at some point:
  * either because it will break easily on any change
  * or, because of initial shortcuts, it cannot meet new needs without major rework
  * or because it is too difficult to use
  * or because its learning curve is too steep for newcomers
  * or it's rather a combination of any of the above reasons.

### Classification of Concrete Build Stacks ###

| Type | Name | Build Manifest Format |
|------|------|-----------------------|
| 4 | Maven | XML |
| 4 | Cargo | init |
| ~4 | Setuptools | Python Call |
| 3 | Autotools | M4 |
| 3 | Make | Make Rules |

<!-- REFERENCES -->
[1]: https://www.sourceware.org/autobook
[2]: https://packaging.python.org
[3]: https://maven.apache.org
[4]: http://doc.crates.io
[5]: http://docs.ansible.com/ansible/index.html
[6]: https://en.wikipedia.org/wiki/Software_build
[7]: https://maven.apache.org/ref/3.3.3/maven-core/lifecycles.html
[9]: https://en.wikipedia.org/wiki/Software_quality_assurance
[10]: https://en.wikipedia.org/wiki/Release_engineering
[11]: https://en.wikipedia.org/wiki/Software_developer

