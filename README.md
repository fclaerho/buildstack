Build stack helper.

"Code" detects the project build stack and drives it to reach well-known targets

Supported build stacks:
  - make
  - python setuptools, pip, twine


**EXAMPLE**

Pick a random project on github:

	$ git clone $something

Use code to poke it:

	$ code clean test


**INSTALLATION**

	$ pip install -i https://pypi.fclaerhout.fr/simple/ code

or, if that repository is not available:

	$ git clone $this
	$ python setup.py install


**DEVELOPMENT**

	$ python setup.py develop
