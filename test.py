# copyright (c) 2014 fclaerhout.fr, released under the MIT license.

import subprocess, tempfile, unittest, textwrap, shutil, sys, os

import build # 3rd-party

class Test(unittest.TestCase):

	def test_make(self):
		# generate a Makefile, check it's detected and run
		dirname = tempfile.mkdtemp()
		with open(os.path.join(dirname, "Makefile"), "w") as f:
			f.write("all: ; touch %s/success" % dirname)
		build.main("-C", dirname, "compile")
		self.assertTrue(os.path.exists(os.path.join(dirname, "success")))
		shutil.rmtree(dirname)

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

# to implement this base class, define two attributes:
#   * tools, the list of tools needed
#   * basename, the source filename
class Model(object):

	tools = ()

	basename = None

	def setUp(self):
		# create a work directory:
		self.dir = tempfile.mkdtemp()
		# generate source file:
		srcpath = os.path.join(self.dir, self.basename)
		with open(srcpath, "w+") as fp:
			fp.write(textwrap.dedent(FILE[self.basename]))
		self.rootname, extname = os.path.splitext(self.basename)
		# generate build manifest:
		self.inipath = os.path.join(self.dir, "build.ini")
		with open(self.inipath, "w+") as fp:
			fp.write("[compile:%s]\npaths: main@%s\n" % (self.rootname, srcpath))

	def tearDown(self):
		# delete work directory:
		shutil.rmtree(self.dir)

	def test(self):
		# check all tools are available, or skip test:
		for tool in self.tools:
			if subprocess.call(("which", tool), stdout = DEVNULL):
				print "%s: tool unavailable for compilation test" % tool
				return
		# build project:
		build.main("-v", "-C", self.dir, "-f", self.inipath, "compile")
		# assert the target has been built:
		tgtpath = os.path.join(self.dir, "target", self.rootname)
		self.assertTrue(
			os.path.exists(tgtpath),
			"%s: target not built" % tgtpath)
		# run the target and check the output is correct:
		output = subprocess.check_output(
			(tgtpath,),
			stderr = sys.stderr)
		self.assertEqual(output, "hello world!\n")

class TestBuiltinJavaCompilation(Model, unittest.TestCase):
	tools = ("javac",)
	basename = "Hello.java"

class TestBuiltinCCompilation(Model, unittest.TestCase):
	tools = ("cc",)
	basename = "hello.c"

class TestBuiltinPythonCompilation(Model, unittest.TestCase):
	tools = ("python2.7", "zip")
	basename = "hello.py"

class TestBuiltinGoCompilation(Model, unittest.TestCase):
	tools = ("go",)
	basename = "hello.go"

class TestBuiltinHaskellCompilation(Model, unittest.TestCase):
	tools = ("ghc",)
	basename = "hello.hs"

if __name__ == "__main__": unittest.main(verbosity = 2)
