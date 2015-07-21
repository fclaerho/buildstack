# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_flush(profileid, filename, targets):
	yield "gradle does not have standard targets"

manifest = {
	"filenames": ("build.gradle",),
	"on_flush": on_flush,
}
