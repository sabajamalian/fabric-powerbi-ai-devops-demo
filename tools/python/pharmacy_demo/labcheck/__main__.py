import sys

from ..cli import main

raise SystemExit(main(["labcheck", *sys.argv[1:]]))
