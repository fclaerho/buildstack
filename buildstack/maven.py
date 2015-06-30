# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

def mvn(filename, profileid, args):
	args = ["mvn"] + list(args)
	if filename:
		args += ["--file", filename]
	if profileid:
		args += ["--activate-profiles", profileids]
	return args

def on_get(profileid, filename, targets, repositoryid, requirementid):
	args = ["org.apache.maven.plugins:maven-dependency-plugin:2.1:get", "--define", "artifact=%s" % requirementid]
	if repositoryid:
		args += ["--define", "repoUrl=%s" % repositoryid]
	yield mvn(
		filename = filename,
		profileid = profileid,
		args = args)

def on_flush(profileid, filename, targets):
	args = []
	while targets:
		target = targets.pop(0)
		if target == "clean":
			if not target.scopeid:
				args.append("clean")
			else:
				yield "%s: unknown clean scope, expected none" % target.scopeid
		elif target == "compile":
			args.append("compile")
		elif target == "test":
			args.append("test")
		elif target == "package":
			args.append("package")
		elif target == "publish":
			args.append("deploy")
		elif target == "install" and not target.uninstall:
			args.append("install")
		else:
			yield "%s: unexpected target" % target
	if args:
		yield mvn(
			filename = filename,
			profileid = profileid,
			args = args)

manifest = {
	"filenames": ["pom.xml"],
	"on_get": on_get,
	"on_flush": on_flush,
	"tool": {
		"maven": {
			"required_vars": ["name", "version"],
			"defaults": {},
			"template": """
				<settings xmlns="http://maven.apache.org/SETTINGS/1.1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
				  xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.1.0 http://maven.apache.org/xsd/settings-1.1.0.xsd">
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
				        <activeByDefault/>
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
				          <id/>
				          <name/>
				          <url/>
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
				      <id/>
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
