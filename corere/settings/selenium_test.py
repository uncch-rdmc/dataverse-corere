# This settings file implements added variables to allow our selenium tests to run
# Currently this is mainly just to disable some git functions in our transitions

from .development import *

SKIP_GIT = True