**Build** is a build stack wrapper — its goal is to abstract the build process
of any source code repository by high-level *well-known targets*.
All build stacks follow the same patterns but all have specific invocation details;
focus on the big picture and let **Build** handle the details…

**Build** understands the following *well-known* targets:
  * `clean [--all]`
  * `test`
  * `compile`
  * `package [--format <id>]`
  * `publish [--repository <id>]`
  * `develop [--uninstall]`
  * `install [--uninstall] [--inventory <id>]`

Example:

	$ git pull ${somewhere}/${some_code_repo}.git
	$ cd ${some_code_repo}
	$ build clean -a test compile package publish -r ${some_pkg_repo}

**Build** can also install modules, `build get <id>`, and configure tools, `build configure <id>`.

For usage details, please check out the inline help: `build -h`

Extra Features
--------------

  * Generate configuration files:
    * ansible
    * nose2, enable xunit standard, useful with Jenkins reporting
    * pypi, to use a private repository
  * Python:
    * use `build package -f pkg` to build native OS/X packages.
    * on testing, if nose2.cfg is present and setup.py does not use it, the original setup.py will be backed up and a new one will be generated to call nose2.
  * Ansible Galaxy:
    * publish your roles to a private http server (e.g. nginx + dav module).
    * Install the dependencies with galaxy from requirements.yml

End-user Installation
---------------------

	$ sudo pip install --extra-index-url https://pypi.fclaerhout.fr/simple/ build

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall build

Developer Installation
----------------------

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall

Plugin Development
------------------

Fill-in the following template and move it to the buildstack directory, it will be loaded automatically.

	def on_clean(profileid, filename, targets, all): pass

	def on_test(profileid, filename, targets): pass

	def on_compile(profileid, filename, targets): pass

	def on_package(profileid, filename, targets, formatid): pass

	def on_publish(profileid, filename, targets, repositoryid): pass

	def on_develop(profileid, filename, targets, uninstall): pass

	def on_install(profileid, filename, targets, uninstall): pass

	def on_flush(profileid, filename, targets): pass

	manifest = {
		#"name": # if unset, use the module name
		"filenames": [], # list of supported build manifest filenames
		#"on_clean": None | on_clean,
		#"on_test": None | on_test,
		#"on_compile": None | on_compile,
		#"on_package": None | on_package,
		#"on_publish": None | on_publish,
		#"on_develop": None | on_develop,
		#"on_install": None | on_install,
		#"on_flush": None | on_flush,
	}

For all handlers, except on_flush, the default behavior is to stack the
target in the 'targets' list. on_flush is called last to unstack those.

All handlers are generators and can yield either "flush", commands or strings.
A command must be a list or tuple of strings as specified by subprocess.call.
A string will be used as an error message.
