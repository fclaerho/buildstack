	  ___         _     
	 / __|___  __| |___ 
	| (__/ _ \/ _` / -_)
	 \___\___/\__,_\___|

Helper designed to detect and drive any project build stack to reach well-known targets:
  * get [-r]: install dependency from a repository -- use a VE if possible
  * clean [-a]: delete objects generated during the build
  * test: run unit tests
  * compile: compile code, for non-interpreted languages
  * package: package code
  * publish [-r]: publish package to a repository
  * develop [-U]: [un]install locally in development mode
  * install [-U,-i]: [un]install locally or [un]provision inventory

See `code --help` for the full list of options.


### EXAMPLE

Clone a random repository on github and use "code" to run its tests, whatever build stack that project may use:

	$ git clone $something
	$ cd $something
	$ code clean test


### END-USER INSTALLATION

	$ pip install -i https://pypi.fclaerhout.fr/simple/ code

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall code


### DEVELOPER INSTALLATION

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall
