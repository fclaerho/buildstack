# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def mvn(filename, profileid, args):
	args = ["mvn"] + list(args)
	if filename:
		args += ["--file", filename]
	if profileid:
		args += ["--activate-profiles", profileids]
	return args

def on_get(profileid, filename, targets, packageid, repositoryid):
	args = ["org.apache.maven.plugins:maven-dependency-plugin:2.1:get", "--define", "artifact=%s" % packageid]
	if repositoryid:
		args += ["--define", "repoUrl=%s" % repositoryid]
	yield mvn(
		filename = filename,
		profileid = profileid,
		args = args)

def on_flush(profileid, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			args.append("clean")
		elif target == "compile":
			args.append("compile")
		elif target == "test":
			args.append("test")
		elif target == "package":
			args.append("package")
		elif target == "publish":
			args.append("deploy")
		elif target == "install" and not target.uninstall:
			args.append("install")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield mvn(
			filename = filename,
			profileid = profileid,
			args = args)

manifest = {
	"filenames": ["pom.xml"],
	"on_get": on_get,
	"on_flush": on_flush,
}
