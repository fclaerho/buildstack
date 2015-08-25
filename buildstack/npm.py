# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

# REF: https://docs.npmjs.com/

def on_get(filename, targets, requirementid):
	yield "@flush",
	if requirementid:
		# This will create the node_modules directory (if one doesn't exist yet),
		# and will download the package to that directory.
		yield "npm", "install", requirementid
	else:
		yield "npm", "update"

#def on_clean(filename, targets): raise NotImplementedError

def on_test(filename, targets): yield "npm", "test"

def on_compile(filename, targets): pass # nothing to do

def on_package(filename, targets, formatid): pass # nothing to do

def on_publish(filename, targets, repositoryid): yield "npm", "publish"

#def on_install(filename, targets, uninstall): raise NotImplementedError

MANIFEST = {
	"filenames": ("package.json",),
	"on_get": on_get,
	#"on_clean": None | on_clean,
	"on_test": on_test,
	"on_compile": on_compile,
	"on_package": on_package,
	"on_publish": on_publish,
	#"on_install": None | on_install,
}