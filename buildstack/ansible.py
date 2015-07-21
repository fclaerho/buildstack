# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

import ConfigParser, yaml, os

###########
# helpers #
###########

cat = lambda *args: args

def get_roles_path():
	parser = ConfigParser.ConfigParser()
	parser.read("ansible.cfg")
	if parser.has_option("defaults", "roles_path"):
		return parser.get("defaults", "roles_path")

#########
# tools #
#########

def galaxy(*args):
	return cat("ansible-galaxy", *args)

def play(filename, *args):
	return cat("ansible-playbook", filename, *args)

############
# handlers #
############

def on_get(profileid, filename, targets, requirementid):
	yield "flush: resolving requirements"
	# create roles_path if it does not exist:
	roles_path = get_roles_path()
	if not os.path.exists(roles_path):
		os.mkdir(roles_path)
	if os.path.exists(requirementid):
		# meet requirements file:
		args = ("--role-file", requirementid)
	else:
		# get single module:
		if not re.match("\w\.\w(,\w)?", requirementid):
			yield "%s: expected id format 'username.rolename[,version]' format" % requirementid
		args = (requirementid,)
	yield galaxy("install", "--force", *args)

def on_clean(profileid, filename, targets, scopeid):
	yield "flush: cleaning requirements"
	# given a requirements file, remove each requirement:
	if os.path.isfile(scopeid):
		with open(scopeid, "r") as fp:
			requirements = yaml.load(fp)
		for req in requirements:
			yield galaxy("remove", req["name"])
		roles_path = get_roles_path()
		if roles_path and os.path.exists(roles_path) and os.listdir(roles_path) == []:
			os.rmdir(roles_path)
	else:
		yield "%s: unknown clean scope, expected requirements file" % scopeid

def on_flush(profileid, filename, targets):
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
			filename = filename,
			*args)

manifest = {
	"filenames": ("playbook.yml", "*.yml"),
	"on_get": on_get,
	"on_clean": on_clean,
	"on_flush": on_flush,
	"tools": {
		"ansible": {
			"required_vars": ("user", "inventory"),
			"defaults": {
				"host_key_checking": "yes",
				"ask_sudo_pass": "no",
				"ask_pass": "no",
				"sudo": "no",
			},
			"template": """
			  # http://docs.ansible.com/intro_configuration.html
				[defaults]
				# ask_pass = True
				# ask_sudo_pass = True
				# bin_ansible_callbacks = False
				# callback_plugins =
				# command_warnings = False
				# connection_plugins =
				# deprecation_warnings = False
				# display_skipped_hosts = False
				# error_on_undefined_vars = False
				# executable = /bin/bash
				# filter_plugins =
				# force_color = 1
				# forks = 5
				# hash_behaviour = merge
				# hostfile = 
				# host_key_checking=True
				# jinja2_extensions =
				# library =
				# log_path =
				# lookup_plugins =
				# module_name =
				# nocolor = 1
				# nocows = 1
				# hosts = *
				# poll_interval = 15
				# private_key_file = /path/to/file.pem
				# remote_port = 22
				# remote_tmp =
				# remote_user =
				# roles_path =
				# sudo_exe =
				# sudo_flags =
				# sudo_user =
				# system_warnings = no
				# timeout = 10
				# record_host_keys = no
				# ssh_args = -o ControlMaster=auto -o ControlPersist=60s
				# control_path=%(directory)s/ansible-ssh-%%h-%%p-%%r
				# scp_if_ssh=False
				# pipelining=False
				# accelerate_port = 5099
				# accelerate_timeout = 30
				# accelerate_connect_timeout = 1.0
				# accelerate_daemon_timeout = 30
				# accelerate_multi_key = yes
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
