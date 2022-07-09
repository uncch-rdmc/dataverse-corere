# This settings file implements added variables to allow our selenium tests to run
# Currently this is mainly just to disable some git functions in our transitions

# TODO: This setting should be closer to production (at least debug off), but there were errors
# - With debug off, our datatable view library is printing caught errors to console which is annoying
# - The middleware needs to bet set up correctly to not whine about missing debug toolbar
# The tests did pass with debug off but for now we'll stick with the below settings

from .development import *

SKIP_GIT = True
SKIP_EDITION = True

MIDDLEWARE.remove("django.middleware.csrf.CsrfViewMiddleware")
