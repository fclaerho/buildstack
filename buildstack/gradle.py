# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def on_flush(filename, targets):
	raise NotImplementedError()

manifest = {
	"filenames": ("build.gradle",),
	"on_flush": on_flush,
}
