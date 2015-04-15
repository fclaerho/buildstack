	   ___       _ __   __
	  / _ )__ __(_) /__/ /
	 / _  / // / / / _  / 
	/____/\_,_/_/_/\_,_/  

	Detect and drive any source code build stack to reach well-known targets.
	
	Usage:
	  build [options] configure <toolid> [<vars>]
	  build [options] get <packageid>
	  build [options] <target>...
	  build --version
	  build --help
	
	Options:
	  -S <path>, --setupscript <path>  force python setup tools as build stack
	  -C <path>, --directory <path>    common, set working directory
	  -M <path>, --makefile <path>     force make as build stack
	  -P <path>, --playbook <path>     force ansible as build stack
	  -r <id>, --repository <id>       with get & publish: select repository
	  -i <id>, --inventory <id>        with install: select inventory
	  -p <ids>, --profiles <ids>       common, comma-separated build profiles
	  -u <name>, --user <name>         common, build on behalf of the specified user
	  -X <path>, --pom <path>          force maven as build stack
	  -f <id>, --format <id>           with package: set format, use '-f help' to list ids
	  -U, --uninstall                  with develop & install: undo
	  -v, --version                    show version
	  -h, --help                       show help
	  -a, --all                        with clean: remove build artifacts
	
	Targets:
	  * configure: generate tool configuration file
	  * get [-r]: install dependency from a repository -- use a VE if possible
	  * clean [-a]: delete objects generated during the build
	  * test: run unit tests
	  * compile: compile code, for non-interpreted languages
	  * package [-f]: package code
	  * publish [-r]: publish package to a repository
	  * develop [-U]: [un]install locally in development mode
	  * install [-U,-i]: [un]install locally or [un]provision inventory
	
	Examples:
	  Run unit tests then cleanup everything:
	    $ build test clean -a
	  Install deliverable as root:
	    $ build install -u root
	  For a python project, export xunit test report:
	    $ build configure nose2
	    $ build test

EXTRA FEATURES
--------------

  * Python:
    * use `package -f pkg` to build native OS/X packages.
    * on testing, if nose2.cfg is present and setup.py does use it, nose2 will be called directly.

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

TODO
----

  * Add debian packaging support to python projects