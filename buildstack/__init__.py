
def get_manifests():
	import pkgutil
	manifests = []
	for loader, modname, _ in pkgutil.iter_modules(__path__):
		mod = loader.find_module(modname).load_module(modname)
		if hasattr(mod, "manifest"):
			if not "name" in mod.manifest:
				mod.manifest["name"] = mod.__name__
			manifests.append(mod.manifest)
	return manifests

manifests = get_manifests()
