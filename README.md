*Build* is a build stack wrapper:
its goal is to abstract the build process of any source code repository through high-level well-known targets.
Focus on the big picture and let *Build* handle the invocation details.

*Build* understands the following well-known targets:
  * get:\<id>             install requirement
  * clean[:all]          delete compilation objects [and build artifacts]
  * compile              compile code
  * test                 run unit tests
  * package[:\<id>]       package code [in the specified format]
  * publish[:\<id>]       publish package [to the specified repository]
  * [un]install[:\<id>]   [un]install locally [or [un]provision inventory]
  * release[:\<id>] [-m]  increment project version, commit and tag

Quick start:

	$ git pull ${somewhere}/${some_code_repo}.git
	$ cd ${some_code_repo}
	$ build clean:all test compile package publish:${some_pkg_repo}

*Build* can also:
  * install requirements via `build get:\<id>`
  * and configure tools via `build configure \<id>`.

For usage details, please check out the inline help: `build -h`

Extra Features
--------------

  * Generate configuration files:
    * ansible
    * nose2, enable xunit standard, useful with Jenkins reporting
    * pypi, to use a private repository
  * Python:
    * use `build package:pkg` to build native OS/X packages.
    * on testing,
		  if `nose2.cfg` is present and setup.py does not use it,
			the original setup.py will be backed up and a new one will be generated to call nose2.

End-User Installation
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

Fill-in the following template and move it to the `buildstack/` directory, it will be loaded automatically.

  def on_get(profileid, filename, targets, requirementid): raise NotImplementedError()
	def on_clean(profileid, filename, targets, all): raise NotImplementedError()
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

For all handlers, except `on_flush`, the default behavior is to stack the target in the `targets` list; `on_flush` is called last to unstack those.
All handlers are generators and can yield either the string `"flush"`, commands or strings.
A command must be a sequence of strings as specified by `subprocess.call()`.
A string is considered to be an error message and raise a BuildError.

