# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def make(filename, args):
	return ["make", "--file", filename] + list(args)

def on_flush(profileid, filename, targets):
	if filename == "configure":
		yield ("./configure",)
		filename = "Makefile"
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			if target.all:
				args.append("clean")
			else:
				args.append("distclean")
		elif target == "test":
			args.append("check")
		elif target == "compile":
			args.append("all")
		elif target == "package":
			args.append("dist")
		elif target == "install":
			args.append("uninstall" if target.uninstall else "install")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield make(filename = filename, args = args)

manifest = {
	"filenames": ["configure", "Makefile", "makefile", "GNUmakefile"],
	"on_get": None,
	"on_flush": on_flush,
}
