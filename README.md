	   ___       _ __   __
	  / _ )__ __(_) /__/ /
	 / _  / // / / / _  / 
	/____/\_,_/_/_/\_,_/  

	Detect and drive any source code build stack to reach well-known targets.
	
	Usage:
	  build [options] get <packageid>
	  build [options] <target>...
	  build --version
	  build --help
	
	Options:
	  -S <path>, --setupscript <path>  force python setup tools as build stack
	  -C <path>, --directory <path>    set working directory
	  -M <path>, --makefile <path>     force make as build stack
	  -P <path>, --playbook <path>     force ansible as build stack
	  -r <id>, --repository <id>       with get & publish: select repository
	  -i <id>, --inventory <id>        with install: select inventory
	  -p <ids>, --profiles <ids>       comma-separated build profiles
	  -u <name>, --user <name>         build on behalf of the specified user
	  -X <path>, --pom <path>          force maven as build stack
	  -f <id>, --format <id>           set package format
	  -U, --uninstall                  with develop & install: undo
	  -v, --version                    show version
	  -h, --help                       show help
	  -a, --all                        with clean: remove build artifacts
	
	Targets:
	  * get [-r]: install dependency from a repository -- use a VE if possible
	  * clean [-a]: delete objects generated during the build
	  * test: run unit tests
	  * compile: compile code, for non-interpreted languages
	  * package [-f]: package code
	  * publish [-r]: publish package to a repository
	  * develop [-U]: [un]install locally in development mode
	  * install [-U,-i]: [un]install locally or [un]provision inventory
	
	Examples:
	  $ build test clean -a   # run unittests then cleanup
	  $ build install -u root # install as root

### END-USER INSTALLATION

	$ pip install -i https://pypi.fclaerhout.fr/simple/ build

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall build

### DEVELOPER INSTALLATION

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall
