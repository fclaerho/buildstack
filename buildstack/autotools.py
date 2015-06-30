# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import os

def on_clean(profileid, filename, targets, scopeid):
	targets.append("clean", scopeid = scopeid)
	yield "flush"
	if scopeid == "all":
		for name in ("ABOUT-GNU", "INSTALL", "config.rpath", "ltconfig",
			"ABOUT-NLS", "NEWS", "config.sub", "ltmain.sh", "AUTHORS", "README",
			"depcomp", "mdat-sh", "BACKLOG", "THANKS", "install-sh", "missing",
			"COPYING", "TODO", "libversion.in", "mkinstalldirs", "COPYING.DOC",
			"ar-lib", "ltcf-c.sh", "py-compile", "COPYING.LESSER", "compile",
			"ltcf-cxx.sh", "texinfo.tex", "COPYING.LIB", "config.guess",
			"ltcf-gcj.sh", "ylwrap", "Changelog"): # list from 'man automake'
			if os.path.islink(name):
				print "removing lingering '%s' (from automake --add-missing)" % name
				os.remove(name)
		for name in ("aclocal.m4", "config.h.in","configure", "Makefile.in", "test-driver"):
			print "removing lingering '%s' (from autotools)" % name
			os.remove(name)

def on_flush(profileid, filename, targets):
	# Invoke Make standard targets:
	# REF: http://www.gnu.org/prep/standards/html_node/Standard-Targets.html
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			if not target.scopeid:
				# delete any file resulting of the build process
				args.append("clean")
			elif target.scopeid == "dist":
				# delete any file that is not part of the source distribution
				args.append("distclean")
			elif target.scopeid in ("all", "maintainer"):
				# delete generated file that should be part of the source distribution, except if autotools-related
				args.append("maintainer-clean")
			else:
				yield "%s: unknown clean scope, expected none, 'dist', 'maintainer' or 'all'" % target.scopeid
		elif target == "compile":
			args.append("all")
		elif target == "test":
			args.append("check")
		elif target == "package":
			args.append("dist")
		elif target == "install":
			args.append("uninstall" if target.uninstall else "install")
		else:
			yield "%s: unexpected target" % target
	if args:
		if not os.path.exists("Makefile"):
			# Generate Makefile with autotools:
			# REF: https://www.sourceware.org/autobook/autobook/autobook_43.html
			yield ("libtoolize",) # => ltmain.sh (to do before aclocal and automake)
			yield ("aclocal",) # configure.ac => aclocal.m4
			yield ("autoconf",) # configure.ac => configure
			yield ("autoheader",) # configure.ac => config.h.in
			yield ("automake", "--add-missing") # Makefile.am => Makefile.in + missing files
			yield ("./configure",) # system state + Makefile.in => Makefile
		yield ["make"] + args

manifest = {
	"filenames": ["configure.ac", "configure.in"],
	"on_get": None,
	"on_clean": on_clean,
	"on_flush": on_flush,
}
