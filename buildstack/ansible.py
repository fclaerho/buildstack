# copyright (c) 2015 fclaerhout.fr, all rights reserved

import os

DISTDIR = "dist"

#########
# tools #
#########

def galaxy(args):
	args = list(args)
	if not os.path.exists("ansible.cfg"):
		args = ["--roles-path", "roles"] + args
	return ["ansible-galaxy", "install"] + args

def play(profileid, username, filename, args):
	args = list(args)
	if username:
		args = ["--user", username] + args
	if profileid:
		args += ["--tags", profileid]
	return ["ansible-playbook", filename] + args

############
# handlers #
############

def on_get(profileid, username, filename, targets, packageid, repositoryid):
	if os.path.exists(packageid):
		# requirements file
		args = ["-r", packageid]
	else:
		# single module
		if not re.match("\w\.\w(,\w)?", packageid):
			raise BuildError("%s: expected 'username.rolename[,version]' format")
		args = [packageid]
	yield galaxy(args)

def on_clean(profileid, username, filename, targets, all):
	if all:
		yield "flush"
		yield ("rm", "-vrf", DISTDIR)

def on_publish(profileid, username, filename, targets, repositoryid):
	yield "flush"
	if not os.path.exists(DISTDIR):
		os.mkdir(DISTDIR)
	for name in os.listdir("roles"):
		srcpath = os.path.join("roles", name)
		tgtpath = os.path.join(DISTDIR, "%s.tgz" % name)
		if os.path.isdir(srcpath):
			yield ("tar", "zcf", tgtpath, "-C", srcpath, ".")
			if target.repositoryid:
				yield ("curl", "-k", "-T", tgtpath, target.repositoryid) # HTTP upload

def on_flush(profileid, username, filename, targets):
	do_play = False
	args = []
	while targets:
		target = targets.pop(0)
		if target == "test":
			args.append("--syntax-check")
		elif target == "install" and not target.uninstall:
			if target.inventoryid:
				args += ["--inventory-file", target.inventoryid]
			else:
				do_play = True
		else:
			yield "%s: unexpected target" % target
	if args or do_play:
		yield play(
			profileid = profileid,
			username = username,
			filename = filename,
			args = args)

manifest = {
	"filenames": ["playbook.yml"],
	"on_get": on_get,
	"on_clean": on_clean,
	"on_publish": on_publish,
	"on_flush": on_flush,
	"tool": {
		"ansible": {
			"required_vars": ["user", "inventory"],
			"defaults": {
				"host_key_checking": "yes",
				"ask_sudo_pass": "no",
				"ask_pass": "no",
				"sudo": "no",
			},
			"template": """
				[defaults]
				host_key_checking = %(host_key_checking)s
				ask_sudo_pass = %(ask_sudo_pass)s
				remote_user = %(user)s
				hostfile = %(inventory)s
				ask_pass = %(ask_pass)s
				# NOTICE: ansible 1.9 breaks the 'sudo' parameter below, downgrade to 1.8.4
				sudo = %(sudo)s
			""",
			"path": "ansible.cfg",
		},
	},
}
