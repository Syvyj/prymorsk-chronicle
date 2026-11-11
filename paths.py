"""Where the data outside this folder lives: the private archive and the folder that goes online.
Another disk or machine: PRYM_ARCHIVE=/path PRYM_PUBLISH=/path (the same names as in the public copy of the code)."""
import os

ARCHIVE = os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive')   # raw copies, private/, video/: never online
PRIVATE = os.path.join(ARCHIVE, 'private')
PUBLISH = os.environ.get('PRYM_PUBLISH', '../prymorsk-publish')   # publish.py assembles the site here
