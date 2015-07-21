# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

# REF: http://yehudakatz.com/2010/12/16/clarifying-the-roles-of-the-gemspec-and-gemfile/

def on_flush(profileid, filename, targets):
	yield "rake does not have standard targets"

manifest = {
	"filenames": ("Rakefile",),
	"on_flush": on_flush,
}
