# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import utils # 3rd-party

#############
# interface #
#############

class Error(utils.Error): pass

class Maintainer(object):

	def __init__(self, name = None, email = None, other = None):
		assert name or email or others
		self.name = name
		self.email = email
		self.other = other

	def __str__(self):
		if self.name and self.email:
			return "%s <%s>" % (self.name, self.email)
		elif self.name:
			return self.name.title()
		elif self.email:
			return "<%s>" % self.email
		elif self.other:
			return self.other

class Repository(object): pass

class Requirement(object): pass

class Manifest(object):

	def __init__(
		self,
		path,
		name,
		version,
		license = None,
		maintainers = None,
		repositories = None,
		requirements = None,
		**kwargs):
		self.path = path
		self.name = name
		self.version = version
		self.license = license or None
		self.maintainers = maintainers or []
		self.repositories = repositories or []
		self.requirements = requirements or []
		self.kwargs = kwargs

	def bumpversion(part):
		if part == "patch":
			raise NotImplementedError
		elif part == "minor":
			raise NotImplementedError
		elif part == "major":
			raise NotImplementedError
		else:
			raise Error(part, "unknown part")

	def dump(self):
		print "path:", self.path
		print "name:", self.name
		print "version:", self.version
		print "license:", self.license
		for idx, obj in enumerate(self.maintainers):
			print "maintainer[%i]:" % idx, obj
		for idx, obj in enumerate(self.repositories):
			print "repository[%i]:" % idx, obj
		for idx, obj in enumerate(self.requirements):
			print "requirement[%i]:" % idx, obj

###################
# implementations #
###################

def copy(src, srckeys, tgt, tgtkey = None, required = False, adapter = lambda obj: obj):
	"do tgt[tgtkey] = adapter(src[srckeys...])"
	obj = src
	for key in srckeys.split("/"):
		if key in obj:
			obj = obj[key]
		else:
			if required:
				raise Exception
	tgt[tgtkey or key] = (adapter)(obj)

def Cargofile(path = "Cargo.toml"):
	path = utils.Path(path)
	src = utils.unmarshall(
		path = path,
		extname = ".cfg")
	tgt = {
		"path": path,
	}
	for key, value in src["package"]:
		if key == "name":
			tgt["name"] = value
		elif key == "version":
			tgt["version"] = value
		elif key == "authors":
			tgt["maintainers"] = map(lambda obj: Maintainer(other = obj), parse(value))
	copy(src, "package/name", tgt, required = True)
	copy(src, "package/version", tgt, required = True)
	copy(src, "package/authors", tgt, "maintainers", required = True, adapter = parse)
	# http://doc.crates.io/manifest.html#the-build-field-(optional)
	copy(src, "package/build", tgt)
	# http://doc.crates.io/manifest.html#the-exclude-and-include-fields-(optional)
	copy(src, "package/exclude", tgt)
	copy(src, "package/include", tgt)
	# http://doc.crates.io/manifest.html#package-metadata
	copy(src, "package/description", tgt)
	copy(src, "package/documentation", tgt)
	copy(src, "package/homepage", tgt)
	copy(src, "package/repository", tgt)
	copy(src, "package/readme", tgt)
	copy(src, "package/keywords", tgt, adapter = parse)
	copy(src, "package/license", tgt)
	copy(src, "package/license-file", tgt)
	# http://doc.crates.io/manifest.html#the-[dependencies.*]-sections
	return Manifest(**kwargs)
