# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

# REF: http://doc.crates.io

def on_flush(profileid, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			args.append("clean")
		elif target == "get":
			args.append("update")
			if target.requirementid:
				args += ["-p", target.requirementid]
		elif target == "compile":
			args.append("build")
			if profileid != "dev":
				args.append("--release")
		elif target == "test":
			args.append("test")
			args.append("bench")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield ["cargo"] + args

manifest = {
	"filenames": ("Cargo.toml",),
	"on_flush": on_flush,
	"tools": {
		"cargo": {
			"required_vars": ("name", "version", "author"),
			"defaults": {},
			"template": """
				[package]
				name = "%(name)s"
				version = "%(version)s"
				authors = ["%(author)s"]
				###
				### http://doc.crates.io/manifest.html#the-build-field-(optional)
				###
				#build = "build.rs"
				###
				### http://doc.crates.io/manifest.html#the-exclude-and-include-fields-(optional)
				###
				#exclude = []
				#include = []
				###
				### http://doc.crates.io/manifest.html#package-metadata
				###
				#description = ""
				#documentation = "<url>"
				#homepage = "<url>"
				#repository = "<url>"
				#readme = "<path>"
				#keywords = []
				#license = ""
				#license-file = "<path>"
				###
				### http://doc.crates.io/manifest.html#the-[dependencies.*]-sections
				###
				#[dependencies]
				#foo = { version = "0.0.1"[, git = "<url>" | path = "<path>"][, optional = true][, features=[]][, default-features = false] }
				#or:
				#foo = "0.0.1" # if fetched from crates.io
				###
				### http://doc.crates.io/manifest.html#the-[profile.*]-sections
				###
				#[profile.(dev|release|test|bench|doc)]
				#opt-level = <int>
				#debug = <bool>
				#rpath = <bool>
				#lto = <bool>
				#debug-assertions = <bool>
				#codegen-units = 1
				###
				### http://doc.crates.io/manifest.html#the-[features]-section
				###
				#[features]
				#default = [<featureid>...]
				#<featureid> = [(<package>|<package/featureid>)...]
				###
				### http://doc.crates.io/manifest.html#configuring-a-target
				###
				#[bin|lib|bench|test]
				#name =
				#path =
				#test = <bool>
				#doctest = <bool>
				#bench = <bool>
				#doc = <bool>
				#plugin = <bool>
				#harness = <bool>
				#crate-type = ["dylib"|"rlib"|"staticlib"]
			""",
			"path": "Cargo.toml",
		}
	}
}
