	  ___         _     
	 / __|___  __| |___ 
	| (__/ _ \/ _` / -_)
	 \___\___/\__,_\___|

Build stack helper.

"Code" detects the project build stack and drives it to reach well-known targets:
  * get [--repository \<repositoryid>] \<packageid>
  * clean [--all]
  * test
  * compile
  * package [--repository \<repositoryid>]
  * publish [--inventory \<repositoryid>]
  * develop [--uninstall]
  * install [--uninstall] [--inventory \<inventoryid>]

Supported build stacks:
  - make
  - python setuptools, pip, twine
  - maven
  - ansible


**EXAMPLE**

Pick a random project on github. Whatever build stack it uses, code abstracts it:

	$ git clone $something
	$ code clean test


**END-USER INSTALLATION**

	$ pip install -i https://pypi.fclaerhout.fr/simple/ code

or, if that repository is not available:

	$ git clone $this
	$ sudo python setup.py install

To uninstall:

	$ sudo pip uninstall code


**DEVELOPER INSTALLATION**

To install:

	$ sudo python setup.py develop

To uninstall:

	$ sudo python setup.py develop --uninstall
