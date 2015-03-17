A build stack helper.


**EXAMPLE**

Pick a random project on github:

	$ git clone $something

Use code to poke it:

	$ code clean test

The build stack will be detected and invoked properly to reach well-known targets.


**INSTALLATION**

	$ pip install -i https://pypi.fclaerhout.fr/simple/ code

or, if that repository is not available:

	$ git clone $this
	$ python setup.py install


**DEVELOPMENT**

	$ python setup.py develop
