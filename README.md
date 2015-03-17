Build stack helper.

"Code" detects the project build stack and drives it to reach well-known targets.

Supported build stacks:
  - make
  - python setuptools, pip, twine


**EXAMPLE**

Pick a random project on github:

	$ git clone $something

Use code to poke it:

	$ code clean test


**END-USER INSTALLATION**

	$ pip install -i https://pypi.fclaerhout.fr/simple/ code

or, if that repository is not available:

	$ git clone $this
	$ python setup.py install

To uninstall:

	$ pip uninstall code


**DEVELOPER INSTALLATION**

To install:

	$ python setup.py develop

To uninstall:

	$ python setup.py develop --uninstall # or code develop -u
