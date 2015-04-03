	 ___      _ _    _ ___ _           _   
	| _ )_  _(_) |__| / __| |_ __ _ __| |__
	| _ \ || | | / _` \__ \  _/ _` / _| / /
	|___/\_,_|_|_\__,_|___/\__\__,_\__|_\_\

Detect and drive any source code build stack to reach well-known targets:
  * get [-r]: install dependency from a repository -- use a VE if possible
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package [-f]: package code
  * publish [-r]: publish package to a repository
  * develop [-U]: [un]install locally in development mode
  * install [-U,-i]: [un]install locally or [un]provision inventory

See `sc --help` for the full list of options.


### EXAMPLE

Clone a random repository on github and use sc to run its tests and package it:

	$ git clone $something
	$ cd $something
	$ sc clean -a test package

### END-USER INSTALLATION

	$ pip install -i https://pypi.fclaerhout.fr/simple/ sc

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall sc


### DEVELOPER INSTALLATION

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall
