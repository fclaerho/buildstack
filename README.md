*NOTICE!
This tool is stable for the use cases it covers but it does not cover all major use cases yet. So far you can build [autotools](https://www.sourceware.org/autobook), [setuptools](https://packaging.python.org), [maven](https://maven.apache.org), [cargo](http://doc.crates.io) and [ansible](http://docs.ansible.com/ansible/index.html)-based projects.*

**Build** is a build stack wrapper:
its goal is to abstract the build process of any source code repository through high-level well-known targets. Focus on the big picture and let **Build** handle the invocation details.

**Build** understands the following well-known targets:
  * `get:<id>` install requirements
  * `clean` delete build byproducts
  * `compile` compile code
  * `run` run project
  * `test` run unit tests
  * `package[:<id>]` package code [in the specified format]
  * `publish[:<id>]` publish package [to the specified repository]
  * `[un]install[:<id>]` [un]install locally [or [un]provision inventory]

Why, oh why?
------------

The target audience is _SQA engineering_, _build engineering_ and _development_ folks
who are all dealing with the same problem: how to quickly build (or run test, or install…)
a project which is using a build stack you're not familiar with?
By using **Build**, check out any repository and build it.
No question asked.
No need to lookup documentation.

	$ git pull $GITSERVER/$MYREPO.git
	$ cd $MYREPO
	$ build clean compile package install

Extra Features
--------------

  * **Build** behavior can be customized through _profiles_, see advanced configuration below.
  * For any build stack, use `build setup <toolid> <vars>…` to instantiate a minimal build manifest.
    Run `build setup help` for the list of supported tools.
  * **Autotools**:
    * better `clean` (remove lingering generated files)
  * **Setuptools**:
    * better `clean` (remove lingering generated files)
    * use `build package:pkg` to build native OS/X packages (on an OS/X platform.)
    * use `build package:deb` to build debian packages (on a debian platform.)
      Install the following tools beforehands:

			$ sudo pip install make-deb
			$ sudo add-apt-repository ppa:dh-virtualenv/daily
			$ sudo apt-get update
			$ sudo apt-get install debhelper dh-virtualenv

    * support the `run` target to execute entry points
    * on testing,
      if `nose2.cfg` is present and setup.py does not use it,
      the original setup.py will be backed up and a new one will be generated to call nose2.

Pre-requisites
--------------

**Build** is not bundled with any build tool, provision the machine appropriately beforehand.

Installation
------------

	$ pip install --user --extra-index-url https://pypi.fclaerhout.fr/simple/ build

or, if that repository is not available:

	$ git clone https://github.com/fclaerho/build.git
	$ python setup.py install --user

Make sure your [user site-packages](https://www.python.org/dev/peps/pep-0370/#specification) bin directory is in your shell `PATH`.

To uninstall:

	$ pip uninstall build

Advanced Configuration
----------------------

Create the file `~/build.json` to customize the commands executed by `build`:

  * before: run commands before
  * after: run commands after
  * append: append extra arguments to the command
  * path: set command path (e.g. on user-wide installation)

You can group customizations into "profiles".
Use the `-p` switch on the command line to select the one you want to use.

For instance, to push after bumpversion (called for a python project on release):

	{
		"all": {
			"bumpversion": {
				"after": [["git", "push", "origin", "master", "--tags"]]
			}
		}
	}

`all` is a particular profile; those customization are applied in all cases.

Or to provision an Ansible inventory as root with a password (on install):

	{
		"as-root": {
			"ansible-playbook": {
				"append": ["--user", "root", "--ask-pass"]
			}
		}
	}

This would be called with `build -p as-root …`.

Adding a Build Stack
--------------------

Fill-in the following template and move it to the `buildstack/` directory, it will be loaded automatically.

	def on_get(filename, targets, requirementid): raise NotImplementedError()
	def on_clean(filename, targets): raise NotImplementedError()
	def on_compile(filename, targets): raise NotImplementedError()
	def on_run(filename, targets, entrypointid): raise NotImplementedError()
	def on_test(filename, targets): raise NotImplementedError()
	def on_package(filename, targets, formatid): raise NotImplementedError()
	def on_publish(filename, targets, repositoryid): raise NotImplementedError()
	def on_install(filename, targets, uninstall): raise NotImplementedError()
	def on_flush(filename, targets): raise NotImplementedError()
	manifest = {
		#"name": # optional, defaults to module name
		"filenames": [], # list of patterns matching supported build manifest filenames
		#"on_get": None | on_get,
		#"on_clean": None | on_clean,
		#"on_compile": None | on_compile,
		#"on_run": None | on_run,
		#"on_test": None | on_test,
		#"on_package": None | on_package,
		#"on_publish": None | on_publish,
		#"on_install": None | on_install,
		#"on_flush": None | on_flush,
	}

For all handlers, except `on_flush`, the default behavior is to stack the target in the `targets` list.
The handler `on_flush` is called last to unstack targets;
**Build** will fail if not all targets have been processed.
The rationale behind this is that most build tools are able to handle multiple targets at the same time and calling them independently is less efficient.
Therefore, when developping a plugin, use target handlers to perform a task that cannot be stacked.

All handlers are generators and can yield either the string `"flush"`, commands or any single object:
  * flush will call on_flush
  * a command must be a sequence of strings as specified by `subprocess.call()`
  * anything else is considered to be an error object and raise a `BuildError()` containing it.

If a command name (i.e. its first element) starts by "@", it is considered to be a builtin call,
e.g. `yield "@trace", "hello, world!"`.
Available built-in functions:
  * `@try(*args)` — on failure, discard exception
  * `@trace(*strings)` — trace execution
  * `@remove(path[, reason])` — remove file or directory

If the build tool does not implement any "clean" target, you may set `"on_clean": "purge",` to use the VCS purge feature (that is, delete untracked files.)

Testing
-------

By default, only the core infrastructure is tested.

To test the build stacks, use: `TESTSTACKS=1 python build.py test clean:all`.
This will check-out various github repositories meeting a standard build process and build them.

If you add new URLs to test, you may use `PAUSE=1 ...` to inspect the output files and specify the corresponding `target_paths` value in the `builds = {}` dictionary.

TODO: This poorman procedure will be replaced soon by docker containers.
