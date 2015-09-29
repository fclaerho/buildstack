# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

cat = lambda *args: args

def on_flush(filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "get":
			# EXPERIMENTAL
			if not target.requirementid:
				yield "oops, unable yet to get all dependencies"
			else:
				args += ["org.apache.maven.plugins:maven-dependency-plugin:2.1:get", "--define", "artifact=%s" % requirementid]
			if repositoryid:
				args += ["--define", "repoUrl=%s" % repositoryid]
		elif target == "clean":
			args.append("clean")
		elif target == "compile":
			args.append("compile")
		elif target == "test":
			args.append("test")
		elif target == "package":
			args.append("package")
		elif target == "publish":
			args.append("deploy")
		elif target == "install":
			args.append("install")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield cat("mvn", "--update-snapshots", "--file", filename, *args)

MANIFEST = {
	"filenames": ("pom.xml",),
	#"on_get" -> flush
	#"on_clean" -> flush
	#"on_compile" -> flush
	"on_run": Exception,
	#"on_test" -> flush
	"on_release": Exception,
	#"on_package" -> flush
	#"on_publish" -> flush
	#"on_install" -> flush
	"on_uninstall": Exception,
	"on_flush": on_flush,
	"tools": {
		"maven": {
			"required_vars": ("url",),
			"defaults": {},
			"template": """
				<settings>
					<localRepository/>
					<interactiveMode/>
					<usePluginRegistry/>
					<offline/>
					<proxies>
						<proxy>
							<active/>
							<protocol/>
							<username/>
							<password/>
							<port/>
							<host/>
							<nonProxyHosts/>
							<id/>
						</proxy>
					</proxies>
					<servers>
						<server>
							<username/>
							<password/>
							<privateKey/>
							<passphrase/>
							<filePermissions/>
							<directoryPermissions/>
							<configuration/>
							<id/>
						</server>
					</servers>
					<mirrors>
						<mirror>
							<mirrorOf/>
							<name/>
							<url/>
							<layout/>
							<mirrorOfLayouts/>
							<id/>
						</mirror>
					</mirrors>
					<profiles>
						<profile>
							<activation>
								<activeByDefault>true</activeByDefault>
								<jdk/>
								<os>
									<name/>
									<family/>
									<arch/>
									<version/>
								</os>
								<property>
									<name/>
									<value/>
								</property>
								<file>
									<missing/>
									<exists/>
								</file>
							</activation>
							<properties>
								<key>value</key>
							</properties>
							<repositories>
								<repository>
									<releases>
										<enabled/>
										<updatePolicy/>
										<checksumPolicy/>
									</releases>
									<snapshots>
										<enabled/>
										<updatePolicy/>
										<checksumPolicy/>
									</snapshots>
									<id>private</id>
									<name>Private Repository</name>
									<url>%(url)s</url>
									<layout/>
								</repository>
							</repositories>
							<pluginRepositories>
								<pluginRepository>
									<releases>
										<enabled/>
										<updatePolicy/>
										<checksumPolicy/>
									</releases>
									<snapshots>
										<enabled/>
										<updatePolicy/>
										<checksumPolicy/>
									</snapshots>
									<id/>
									<name/>
									<url/>
									<layout/>
								</pluginRepository>
							</pluginRepositories>
							<id>default</id>
						</profile>
					</profiles>
					<activeProfiles/>
					<pluginGroups/>
				</settings>
			""",
			"path": "~/.m2/settings.xml",
		},
	},
}
