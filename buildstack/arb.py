# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_flush(profileid, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			if not target.scopeid:
				args.append("clean")
			elif target.scopid == "all":
				args += ["clean", "--all"]
			else:
				yield "%s: unknown scope, expected none or 'all'" % target.scopeid
		elif target == "test":
			args.append("check")
		elif target == "compile":
			args.append("compile")
		elif target == "package":
			args.append("package")
		elif target == "publish":
			if target.repositoryid:
				args += ["publish", "-r", target.repositoryid]
			else:
				args.append("publish")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield ["arb"] + args

manifest = {
	"filenames": ["meta/main.yml"],
	"on_flush": on_flush,
}
