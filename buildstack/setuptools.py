# copyright (c) 2015 fclaerhout.fr, all rights reserved

import glob, os, re

#########
# tools #
#########

def pip(username, args):
	args = ["pip"] + list(args)
	if username:
		args = ["sudo", "-u", username] + args
	return args

def setup(filename, username, args):
	args = ["python", filename] + list(args)
	if username:
		args = ["sudo", "-u", username] + argv
	return args

def twine(username, args):
	args = ["twine"] + list(args)
	if username:
		args = ["sudo", "-u", username] + args
	return args

def get(self, username, packageid, repositoryid = None):
	args = ["install"]
	if os.path.exists(packageid):
		# requirements file
		args += ["-r", packageid]
	else:
		# single module
		args += [packageid]
	if repositoryid:
		args += ["--extra-index-url", repositoryid]
	return pip(
		username = username,
		args = args)

############
# handlers #
############

def on_get(profileid, username, filename, targets, packageid, repositoryid):
	args = ["install"]
	if os.path.exists(packageid):
		# requirements file
		args += ["-r", packageid]
	else:
		# single module
		args += [packageid]
	if repositoryid:
		args += ["--extra-index-url", repositoryid]
	yield pip(
		username = username,
		args = args)

def on_clean(profileid, username, filename, targets, all):
	if all:
		targets.append("clean", all = True)
		yield "flush"
		yield ["rm", "-vrf", ".virtualenv", "dist", ".eggs", "nose2-junit.xml"] + glob.glob("*.egg-info")
		yield ("find", ".", "-name", "*.pyc", "-delete")
	else:
		targets.append("clean")

def on_test(profileid, username, filename, targets):
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
	yield "flush"

def on_package(profileid, username, filename, targets, formatid):
	if formatid == "pkg":
		# *** EXPERIMENTAL ***
		args += ["bdist", "--format=tar"]
		yield setup(
			filename = filename,
			username = username,
			args = args)
		for path in glob.glob("dist/*.tar"):
			yield ("mkdir", "-p", "dist/root")
			yield ("tar", "-C", "dist/root", "-xf", path)
			basename, extname = os.path.splitext(path)
			name, tail = basename.split("-", 1)
			version, _ = tail.split(".macosx", 1)
			identifier = "fr.fclaerhout.%s" % name # FIXME
			yield ("pkgbuild", basename + ".pkg", "--root", "dist/root", "--version", version, "--identifier", identifier)
	else:
		targets.append("package", formatid = formatid)

def on_publish(profileid, username, filename, targets, repositoryid):
	yield "flush"
	args = ["upload"] + glob.glob("dist/*")
	if repositoryid:
		args += ["--repository", repositoryid]
	yield twine(
		username = username,
		args = args)

def on_install(filename, username, targets, inventoryid, uninstall):
	if uninstall:
		yield "flush"
		yield pip("uninstall", os.path.basename(os.getcwd()))
	else:
		targets.append("install")

def on_flush(profileid, username, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			args.append("clean")
			if target.all:
				args.append("--all")
		elif target == "test":
			args.append("test")
		elif target == "compile":
			args.append("build")
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
				"deb": lambda: args,
				"pkg": lambda: args,
			}
			if not target.formatid:
				target.formatid = "sdist"
			elif formatid == "help":
				raise SystemExit("\n".join(func.keys()))
			func[target.formatid]()
		elif target == "develop":
			args.append("develop")
			if target.uninstall:
				args.append("--uninstall")
		elif target == "install":
			args.append("install")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield setup(
			filename = filename,
			username = username,
			args = args)

manifest = {
	"filenames": ["setup.py"],
	"on_get": on_get,
	"on_clean": on_clean,
	"on_test": on_test,
	"on_package": on_package,
	"on_publish": on_publish,
	"on_install": on_install,
	"on_flush": on_flush,
	"tool": {
		"nose2": {
			"required_vars": [],
			"defaults": {},
			"template": """
				[unittest]
				plugins = nose2.plugins.junitxml
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
				[distutils]
				index-servers = %(name)s
				[%(name)s]
				repository = %(url)s
				username = %(user)s
				password = %(pass)s
			""",
			"path": "~/.pypirc",
		},
	},
}
