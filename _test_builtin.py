# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

import subprocess, tempfile, unittest, textwrap, shutil, sys, os

DEVNULL = open(os.devnull, "w")

FILE = {
	"Hello.java": """
		class Hello {
			public static void main(String[] argv) {
				System.out.println("hello world!");	
			}
		}
	""",
	"hello.c": """
		#include <stdio.h>
		int main(void) {
			printf("hello world!\\n");
			return 0;
		}
	""",
	"hello.go": """
		package main
		import "fmt"
		func main() {
			fmt.Println("hello world!")
		}
	""",
	"hello.py": "print 'hello world!'",
	"hello.hs": """
		main = putStrLn "hello world!"
	""",
}

class Model(object):

	basename = None

	def setUp(self):
		self.dir = tempfile.mkdtemp()
		srcpath = os.path.join(self.dir, self.basename)
		with open(srcpath, "w+") as fp:
			fp.write(textwrap.dedent(FILE[self.basename]))
		self.rootname, extname = os.path.splitext(self.basename)
		self.inipath = os.path.join(self.dir, "build.ini")
		with open(self.inipath, "w+") as fp:
			fp.write("[compile:%s]\npaths: main@%s\n" % (self.rootname, srcpath))

	def tearDown(self):
		shutil.rmtree(self.dir)

	def test(self):
		for tool in self.tools:
			if subprocess.call(("which", tool), stdout = DEVNULL):
				print "%s: tool unavailable for compilation test" % tool
				return
		subprocess.check_call(
			("target/build", "-f", self.inipath, "-b", self.dir, "compile"),
			stdout = sys.stdout,
			stderr = sys.stderr)
		self.assertTrue(os.path.exists(os.path.join(self.dir, self.rootname)))
		output = subprocess.check_output(
			(os.path.join(self.dir, self.rootname),),
			stderr = sys.stderr)
		self.assertEqual(output, "hello world!\n")

class TestJavaCompilation(Model, unittest.TestCase):
	tools = ("javac",)
	basename = "Hello.java"

class TestCCompilation(Model, unittest.TestCase):
	tools = ("cc",)
	basename = "hello.c"

class TestPythonCompilation(Model, unittest.TestCase):
	tools = ("python2.7",)
	basename = "hello.py"

class TestGoCompilation(Model, unittest.TestCase):
	tools = ("go",)
	basename = "hello.go"

class TestHaskellCompilation(Model, unittest.TestCase):
	tools = ("ghc",)
	basename = "hello.hs"

if __name__ == "__main__": unittest.main(verbosity = 2)
