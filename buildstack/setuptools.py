# copyright (c) 2015 fclaerhout.fr, released under the MIT license.
# coding: utf-8

import shutil, glob, os, re

#########
# tools #
#########

def pip(args):
	return ["pip"] + list(args)

def setup(filename, args):
	return ["python", filename] + list(args)

def twine(args):
	return ["twine"] + list(args)

def bumpversion(args):
	return ["bumpversion"] + list(args)

############
# handlers #
############

def on_get(profileid, filename, targets, requirementid):
	args = ["install"]
	if os.path.exists(requirementid):
		# requirements file
		args += ["--requirement", requirementid]
	else:
		# single module
		args += [requirementid]
	yield pip(args)

def on_clean(profileid, filename, targets):
	targets.append("clean")
	yield "flush: removing lingering files"
	# remove *.pyc and *.pyo files
	for dirname, _, basenames in os.walk("."):
		for basename in basenames:
			_, extname = os.path.splitext(basename)
			if extname in (".pyc", ".pyo"):
				print "removing lingering '%s' (bytecode)" % basename
				path = os.path.join(dirname, basename)
				os.remove(path)
	# cleanup dist
	for name in glob.glob("dist") + glob.glob("*.egg-info"):
		print "removing lingering '%s' (packaging)" % name
		shutil.rmtree(name)
	# cleanup requirements
	for name in glob.glob("*.egg*"):
		print "removing lingering '%s' (requirement)" % name
		if os.path.isdir(name):
			shutil.rmtree(name)
		else:
			os.remove(name)

def on_test(profileid, filename, targets):
	# if nose2 configuration file exists, use nose2 as test framework
	text = open(filename).read()
	if os.path.exists("nose2.cfg") and "nose2.collector.collector" not in text:
		with open("%s.bak" % filename, "w") as f:
			f.write(text)
		text = re.sub("test_suite.*?,", "test_suite = \"nose2.collector.collector\",", text)
		with open(filename, "w") as f:
			f.write(text)
	targets.append("test")
	# Setuptools BUG?
	# - "python setup.py sdist test" handles both targets as expected
	# - "python setup.py test sdist" handles "test" only :-(
	# solution: flush targets after test
	yield "flush: working around setuptools issue"

# *** EXPERIMENTAL ***
def on_package(profileid, filename, targets, formatid):
	# build OS/X package:
	if formatid == "pkg":
		args += ["bdist", "--format=tar"]
		yield setup(
			filename = filename,
			args = args)
		for path in glob.glob("dist/*.tar"):
			yield ("mkdir", "-p", "dist/root")
			yield ("tar", "-C", "dist/root", "-xf", path)
			basename, extname = os.path.splitext(path)
			name, tail = basename.split("-", 1)
			identifier = raw_input("identifier (e.g. fr.fclaerhout.%s)?" % name)
			yield ("pkgbuild", basename + ".pkg", "--root", "dist/root", "--version", version, "--identifier", identifier)
	# build debian package:
	elif formatid == "deb":
		# REF: https://nylas.com/blog/packaging-deploying-python
		yield ("make-deb",) # generates inputs to dh_virtualenv and calls it
		#TODO: generate requirements.txt from setup.py
		yield ("dpkg-buildpackage", "-us", "-uc")
	# or let setuptools handle the packaging:
	else:
		targets.append("package", formatid = formatid)

def on_publish(profileid, filename, targets, repositoryid):
	yield "flush: publishing package"
	args = ["upload"] + glob.glob("dist/*")
	if repositoryid:
		args += ["--repository", repositoryid]
	yield twine(args)

def on_install(profileid, filename, targets, inventoryid, uninstall):
	if uninstall:
		yield "flush: uninstalling"
		yield pip(("uninstall", os.path.basename(os.getcwd())))
	else:
		targets.append("install")

def on_release(profileid, filename, targets, typeid, message):
	yield "flush: releasing"
	args = [typeid]
	if message:
		args = ["--message", message] + args
	yield bumpversion(args)

def on_flush(profileid, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			args += ["clean", "--all"]
		elif target == "compile":
			args.append("build")
		elif target == "test":
			args.append("test")
		elif target == "package":
			func = {
				"sdist": lambda: args.append("sdist"),
				"sdist:zip": lambda: args.extend(["sdist", "--format=zip"]),
				"sdist:gztar": lambda: args.extend(["sdist", "--format=gztar"]),
				"sdist:bztar": lambda: args.extend(["sdist", "--format=bztar"]),
				"sdist:ztar": lambda: args.extend(["sdist", "--format=ztar"]),
				"sdist:tar": lambda: args.extend(["sdist", "--format=tar"]),
				"bdist": lambda: args.append("bdist"),
				"bdist:gztar": lambda: args.extend(["sdist", "--format=gztar"]), # unix default
				"bdist:ztar": lambda: args.extend(["sdist", "--format=ztar"]),
				"bdist:tar": lambda: args.extend(["sdist", "--format=tar"]),
				"bdist:zip": lambda: args.extend(["sdist", "--format=zip"]), # windows default
				"rpm": lambda: args.extend(["sdist", "--format=rpm"]),
				"pkgtool": lambda: args.extend(["sdist", "--format=pkgtool"]),
				"sdux": lambda: args.extend(["sdist", "--format=sdux"]),
				"wininst": lambda: args.extend(["sdist", "--format=wininst"]),
				"msi": lambda: args.extend(["sdist", "--format=msi"]),
			}
			if not target.formatid:
				target.formatid = "sdist"
			elif target.formatid == "help":
				raise SystemExit("\n".join(["deb", "pkg"] + func.keys()))
			elif target.formatid not in func:
				yield "%s: unsupported format id" % target.formatid
			func[target.formatid]()
		elif target == "install":
			args.append("install")
			if target.uninstall:
				args.append("--uninstall")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield setup(
			filename = filename,
			args = args)

manifest = {
	"filenames": ("setup.py",),
	"on_get": on_get,
	"on_clean": on_clean,
	"on_test": on_test,
	"on_package": on_package,
	"on_publish": on_publish,
	"on_install": on_install,
	"on_release": on_release,
	"on_flush": on_flush,
	"tools": {
		"setuptools": {
			"required_vars": ("name", "version",),
			"defaults": {},
			"template": """
				# REF: https://packaging.python.org
				
				import setuptools
				
				setuptools.setup(
					name = "%(name)s", # https://www.python.org/dev/peps/pep-0426/#name
					version = "%(version)s", # https://www.python.org/dev/peps/pep-0440/
					#packages = []|setuptools.find_packages(), # https://pythonhosted.org/setuptools/setuptools.html#using-find-packages
					#description = "",
					#long_description = "",
					#url = "", # https://docs.python.org/2/distutils/setupscript.html#additional-meta-data
					#author = "",
					#author_email = "",
					#license = "",
					#classifiers = [], # https://pypi.python.org/pypi?%%3Aaction=list_classifiers
					#keyword = [],
					#py_modules = [],
					#install_requires = [], # https://packaging.python.org/en/latest/requirements.html#install-requires-vs-requirements-files
					#package_data = {}, # https://docs.python.org/2/distutils/setupscript.html#installing-package-data
					#data_files = {}, # https://docs.python.org/2/distutils/setupscript.html#installing-additional-files
					#entry_points = {}, # https://pythonhosted.org/setuptools/setuptools.html#automatic-script-creation
					#test_suite = "",
					#tests_require = [],
					#extra_require = {},
					#setup_requires = [],
					#dependency_links = [], # https://pythonhosted.org/setuptools/setuptools.html#dependencies-that-aren-t-in-pypi
					#scripts = [], # https://docs.python.org/2/distutils/setupscript.html#installing-scripts
				)
			""",
			"path": "setup.py",
		},
		"bumpversion": {
			"required_vars": ["current_version"],
			"defaults": {},
			"template": """
				# REF: https://github.com/peritus/bumpversion
				
				[bumpversion]
				current_version = %(current_version)s
				#new_version=
				commit = True
				tag = True
				#tag_name = v{new_version}
				#message = Bump version: {current_version} → {new_version}
				#parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)
				#serialize = {major}.{minor}.{patch}
				
				#[bumpversion:part:<name>]
				#values =
				#optional_values =
				#first_value =
				
				[bumpversion:file:setup.py]
				#search = {current_version}
				#replace = {new_version}
			""",
			"path": ".bumpversion.cfg",
		},
		"nose2": {
			"required_vars": [],
			"defaults": {},
			"template": """
				# REF: http://nose2.readthedocs.org/en/latest/configuration.html
				
				[unittest]
				#start-dir =
				#code-directories =
				#test-file-pattern =
				#test-method-prefix
				plugins = nose2.plugins.junitxml
				#exclude-plugins =
				
				[junit-xml]
				always-on = True
				
				[load_tests]
				always-on = True
			""",
			"path": "nose2.cfg",
		},
		"pypi": {
			"required_vars": ["name", "url", "user", "pass"],
			"defaults": {},
			"template": """
				# REF: https://docs.python.org/2/distutils/packageindex.html#the-pypirc-file
				
				[distutils]
				index-servers = %(name)s
				
				[%(name)s]
				repository = %(url)s
				username = %(user)s
				password = %(pass)s
			""",
			"path": "~/.pypirc",
		},
		"pip": {
			"required_vars": ["extra_index_url"],
			"defaults": {},
			"template": """
				# REF: https://pip.pypa.io/en/latest/user_guide.html#configuration
				[global]
				#proxy =
				#index-url =
				extra-index-url = %(extra_index_url)s
			""",
			"path": "~/.pip/pip.conf",
		},
		"easy_install": {
			"required_vars": ["index_url"],
			"defaults": {},
			"template": """
				# REF: https://pythonhosted.org/setuptools/easy_install.html#configuration-files
				[easy_install]
				#install_dir =
				index_url = %(index_url)s
			""",
			"path": "~/.pydistutils.cfg",
		},
	},
}
