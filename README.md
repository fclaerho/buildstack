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

For usage and development details, please check out the inline help: `build -h`

EXTRA FEATURES
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

END-USER INSTALLATION
---------------------

	$ sudo pip install --extra-index-url https://pypi.fclaerhout.fr/simple/ build

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall build

DEVELOPER INSTALLATION
----------------------

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall

Add your extensions into the `buildstack/` directory, they will be loaded automatically.
