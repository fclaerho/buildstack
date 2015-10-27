# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

cat = lambda *args: args

def on_flush(filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			args.append("clean")
		elif target == "compile":
			args.append("dist")
		elif target == "test":
			args.append("check")
		elif target == "package":
			args.append("package")
		elif target == "publish":
			args.append("publish")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield cat("ansible-universe", *args)

MANIFEST = {
	"filenames": ["meta/main.yml"],
	"on_get": Exception,
	#"on_clean" -> flush
	#"on_compile" -> flush
	"on_run": Exception,
	#"on_test" -> flush
	"on_release": Exception,
	#"on_package" -> flush
	#"on_publish" -> flush
	"on_install": Exception,
	"on_uninstall": Exception,
	"on_flush": on_flush,
	"tools": {},
}
