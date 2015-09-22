
*NOTICE!
This tool is stable for the use cases it covers but it does not cover all major use cases yet.
So far you can build
[autotools](https://www.sourceware.org/autobook),
[setuptools](https://packaging.python.org),
[maven](https://maven.apache.org),
[cargo](http://doc.crates.io)
and [ansible](http://docs.ansible.com/ansible/index.html)-based projects.*

**BuildStack** is a wrapper around build tools and their ecosystem:
its goal is to abstract the build process of any source code repository
by driving the underlying build stack through _well-known targets_.
Focus on the big picture and let **BuildStack** handle the details.

The following _well-known targets_ are supported:
  * `get:ID` install requirements
  * `clean` delete build byproducts
  * `compile` compile code
  * `run` run project
  * `test` run unit tests
  * `package[:ID]` package code [in the specified format]
  * `publish[:ID]` publish package [to the specified repository]
  * `[un]install[:ID]` [un]install locally [or [un]provision inventory]
  * `release:ID [-m]` bump version, commit and tag source code

The following _[lifecycles](https://maven.apache.org/ref/3.3.3/maven-core/lifecycles.html)_ are supported:
  * run: `compile` < `run`
  * clean: `clean`
  * install: `compile` < `test` < `package` < `install`
  * publish: `compile` < `test` < `package` < `publish`
  * release: `compile` < `test` < `release`


Why, Oh Why?
------------

_SQA engineers_, _build engineers_ and _developers_ are all dealing with the same problem:
how to quickly build and use a project using a build stack they are not familiar with?
By using **BuildStack**, check out any repository and reach your build targets.
No question asked and no need to lookup documentation.

	$ git pull $HOST/$FOO.git
	$ build -C $FOO clean test # automatically triggers 'compile'


Extra Features
--------------

  * Lifecycles support.
  * Instantiate tool configuration templates, see `build setup help`.
  * **Autotools**:
    * better `clean` (remove lingering generated files)
  * **Setuptools**:
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

**BuildStack** is not bundled with any build tool;
provision the machine appropriately beforehand.


Installation
------------

	$ pip install --user buildstack

or, if the PyPI repository is not available:

	$ pip install --user git+https://github.com/fclaerho/buildstack.git

The package will be installed in your [user site-packages](https://www.python.org/dev/peps/pep-0370/#specification) directory; make sure its `bin/` sub-directory is in your shell lookup path.

To uninstall:

	$ pip uninstall buildstack


Advanced Configuration
----------------------

Create the file `~/buildstack.json` to customize each command executed by `build`:

  * before: run commands before
  * after: run commands after
  * append: append extra arguments to the command
  * path: set command path (e.g. on user-wide installation)

You can group customizations into "profiles",
use the `-p, --profile` switch on the command line to select the one to use.

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

To calculate the new version, **BuildStack** passes the `Version` class to your release handler — of course, you can ignore this argument if you have another mean to do version calculation.
  * `Version.parse_stdout(*args)` — return version instance from the command output (it should match N(.N)*)
  * `version.bump(partid)` — return bumped version, where partid is (major|minor|patch) or an index.

### Testing ###

You can use buildstack to test itself without installing it, given its dependencies are present:

	$ python -m buildstack test

Otherwise:

	$ python setup.py test

To test concrete build stacks, build the provided docker files.
