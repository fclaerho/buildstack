# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_flush(profileid, filename, targets):
	raise NotImplementedError()

manifest = {
	"filenames": ("Gruntfile.coffee", "Gruntfile.js"),
	"on_flush": on_flush,
}
