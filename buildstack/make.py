
def make(filename, username, args):
	args = ["make", "--file", filename] + list(args)
	if username:
		args = ["sudo", "-u", username] + args
	return args

def on_flush(profileid, username, filename, targets):
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
		yield make(filename = filename, username = username, args = args)

manifest = {
	"filenames": ["Makefile", "makefile", "GNUmakefile"],
	"on_get": None,
	"on_flush": on_flush,
}
