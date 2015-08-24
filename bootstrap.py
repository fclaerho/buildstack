# copyright (c) 2015 fclaerhout.fr, released under the MIT license.

"allow to run buildstack without installing it"

import buildstack, sys

buildstack.main(*sys.argv[1:])
