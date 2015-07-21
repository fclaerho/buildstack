*NOTICE!
This tool is stable for the use cases it covers but it does not cover all major use cases yet. So far you can build [autotools](https://www.sourceware.org/autobook), [setuptools](https://packaging.python.org), [maven](https://maven.apache.org), [cargo](http://doc.crates.io) and [ansible](http://docs.ansible.com/ansible/index.html)-based projects.*

**Build** is a build stack wrapper:
its goal is to abstract the build process of any source code repository through high-level well-known targets. Focus on the big picture and let **Build** handle the invocation details.

**Build** understands the following well-known targets:
  * `get:<id>`             install requirement
  * `clean`          delete compilation objects [and build artifacts]
  * `compile`              compile code
  * `test`                 run unit tests
  * `package[:<id>]`       package code [in the specified format]
  * `publish[:<id>]`       publish package [to the specified repository]
  * `[un]install[:<id>]`   [un]install locally [or [un]provision inventory]
  * `release[:<id>] [-m]`  bump project version, commit and tag

Why, oh why?
------------

The target audience is SQA engineering, build engineering and development people.

Here's the killer use case: check out any repository and build it. No question asked.

	$ git pull $GITSERVER/$MYREPO.git
	$ cd $MYREPO
	$ build clean compile package install

If you're a developer, being able to test and release your code in one step is neat too:

	$ build test clean:all release:patch -m "fix bug foobar"

Extra Features
--------------

  * Can instantiate configuration file templates,
    run `build configure help` for the list of supported tools.
  * Autotools:
    * better `clean` (remove lingering generated files)
  * Setuptools:
    * better `clean` (remove lingering generated files)
    * use `build package:pkg` to build native OS/X packages (on an OS/X platform.)
    * use `build package:deb` to build debian packages (on a debian platform.)
      Install the following tools beforehands:

			$ sudo pip install make-deb
			$ sudo add-apt-repository ppa:dh-virtualenv/daily
			$ sudo apt-get update
			$ sudo apt-get install debhelper dh-virtualenv

    * on testing,
      if `nose2.cfg` is present and setup.py does not use it,
      the original setup.py will be backed up and a new one will be generated to call nose2.

Pre-requisites
--------------

**Build** is not bundled with any build stack.
Make sure to install your compiler and other tools beforehand.

Installation
------------

	$ sudo pip install --extra-index-url https://pypi.fclaerhout.fr/simple/ build

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall build

Advanced Configuration
----------------------

You can create the `~/build.json` to customize the commands executed by `build`:

  * before: run commands before
  * after: run commands after
  * append: append extra arguments to the command
  * path: set command path (e.g. on user-wide installation)

For instance, to push after bumpversion (called for a python project on release):

	{
		"all": {
			"bumpversion": {
				"after": [["git", "push", "origin", "master", "--tags"]]
			}
		}
	}

`all` means "for all profile".

Or to provision an Ansible inventory as root with a password (on install):

	{
		"asroot": {
			"ansible-playbook": {
				"append": ["--user", "root", "--ask-pass"]
			}
		}
	}

Specifying a profile means you have to call `build -p asroot ...` to use the customization.

Plugin Development
------------------

Fill-in the following template and move it to the `buildstack/` directory, it will be loaded automatically.

	def on_get(profileid, filename, targets, requirementid): raise NotImplementedError()
	def on_clean(profileid, filename, targets): raise NotImplementedError()
	def on_test(profileid, filename, targets): raise NotImplementedError()
	def on_compile(profileid, filename, targets): raise NotImplementedError()
	def on_package(profileid, filename, targets, formatid): raise NotImplementedError()
	def on_publish(profileid, filename, targets, repositoryid): raise NotImplementedError()
	def on_install(profileid, filename, targets, uninstall): raise NotImplementedError()
	def on_flush(profileid, filename, targets): raise NotImplementedError()
	manifest = {
		#"name": # if unset, use the module name
		"filenames": [], # list of supported build manifest filenames
		#"on_get": None | on_get,
		#"on_clean": None | on_clean,
		#"on_test": None | on_test,
		#"on_compile": None | on_compile,
		#"on_package": None | on_package,
		#"on_publish": None | on_publish,
		#"on_install": None | on_install,
		#"on_flush": None | on_flush,
	}

For all handlers, except `on_flush`, the default behavior is to stack the target in the `targets` list. The handler `on_flush` is called last to unstack targets and build will fail if not all targets have been processed. All handlers are generators and can yield either the string `"flush"`, commands or strings. A command must be a sequence of strings as specified by `subprocess.call()`. A string is considered to be an error message and raise a `BuildError()`. If a command image (i.e. its first element) starts by "@", it is considered to be a function name, e.g. `yield ("@trace", "hello, world!")` — see the available functions below.

Available built-in functions:
  * `@trace(*strings)` — trace execution
  * `@remove(path[, reason])` — remove file or directory

If the build tool does not implement any "clean" target, you may set `"on_clean": "purge",` to use the VCS purge feature (that is, delete untracked files.)

Testing
-------

By default, only the core infrastructure is tested.

To test the build stacks, use: `TESTSTACKS=1 python build.py test clean:all`

If you add new URLs to test, you may use `PAUSE=1 ...` to inspect the output files and specify the corresponding `target_paths` value in the `builds = {}` dictionary.
