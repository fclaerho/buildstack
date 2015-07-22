# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_flush(filename, targets):
	raise NotImplementedError()

manifest = {
	"filenames": ("build.xml",),
	"on_flush": on_flush,
}
