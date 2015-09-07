# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import os

cat = lambda *args: args

def on_clean(filename, targets):
	targets.append("clean")
	yield "@flush",
	for name in ("ABOUT-GNU", "INSTALL", "config.rpath", "ltconfig",
		"ABOUT-NLS", "NEWS", "config.sub", "ltmain.sh", "AUTHORS", "README",
		"depcomp", "mdat-sh", "BACKLOG", "THANKS", "install-sh", "missing",
		"COPYING", "TODO", "libversion.in", "mkinstalldirs", "COPYING.DOC",
		"ar-lib", "ltcf-c.sh", "py-compile", "COPYING.LESSER", "compile",
		"ltcf-cxx.sh", "texinfo.tex", "COPYING.LIB", "config.guess",
		"ltcf-gcj.sh", "ylwrap", "Changelog"): # list from 'man automake'
		if os.path.islink(name):
			yield "@remove", name, "lingering from automake --add-missing"
	for name in ("aclocal.m4", "config.h.in","configure", "Makefile.in", "test-driver"):
		if os.path.exists(name):
			yield "@remove", name, "lingering from autotools"

def on_flush(filename, targets):
	# Invoke Make standard targets:
	# REF: http://www.gnu.org/prep/standards/html_node/Standard-Targets.html
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			# clean: delete files generated by make
			# distclean: delete files generated by configure
			# maintainer-clean: delete most files generated by autotools
			args.append("maintainer-clean")
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
			# Bootstrap method; generate Makefile with autotools:
			# REF: https://www.sourceware.org/autobook/autobook/autobook_43.html
			# TL;DR: don't use autoreconf.
			yield "libtoolize", # => ltmain.sh (to do before aclocal and automake)
			yield "aclocal", # configure.xx => aclocal.m4
			yield "autoconf", # configure.xx => configure
			with open(filename, "r") as fp:
				text = fp.read()
				if "AC_CONFIG_HEADERS" in text or "AM_CONFIG_HEADER" in text:
					yield "autoheader", # configure.xx => config.h.in
				else:
					yield "@trace", "no _CONFIG_HEADER, skipping autoheader"
			if os.path.exists("Makefile.am"):
				# you'll also need AM_INIT_AUTOMAKE() in configure.xx
				yield "automake", "--add-missing" # configure.xx + Makefile.am => Makefile.in + missing files
			yield "./configure", # system state [+ Makefile.in?] => Makefile
		yield cat("make", *args)

MANIFEST = {
	"filenames": ("configure.ac", "configure.in", "Makefile"),
	"on_get": None,
	"on_clean": on_clean,
	"on_flush": on_flush,
}
