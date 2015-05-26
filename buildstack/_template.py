# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_clean(profileid, username, filename, targets, all): pass

def on_test(profileid, username, filename, targets): pass

def on_compile(profileid, username, filename, targets): pass

def on_package(profileid, username, filename, targets, formatid): pass

def on_publish(profileid, username, filename, targets, repositoryid): pass

def on_develop(profileid, username, filename, targets, uninstall): pass

def on_install(profileid, username, filename, targets, uninstall): pass

def on_flush(profileid, username, filename, targets): pass

manifest = {
	#"name":
	"filenames": [],
	#"on_clean": None | on_clean,
	#"on_test": None | on_test,
	#"on_compile": None | on_compile,
	#"on_package": None | on_package,
	#"on_publish": None | on_publish,
	#"on_develop": None | on_develop,
	#"on_install": None | on_install,
	#"on_flush": None | on_flush,
}
