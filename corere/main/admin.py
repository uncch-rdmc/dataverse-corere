from django.contrib import admin
from .models import Verification, Curation, File, Submission, Manuscript, User
from django.contrib.auth.models import Permission, Group
from guardian.admin import GuardedModelAdmin

# Register your models here.

admin.site.register(Verification)
admin.site.register(Curation)
admin.site.register(File)
admin.site.register(Submission)
admin.site.register(Manuscript, GuardedModelAdmin)
admin.site.register(User, GuardedModelAdmin)
#admin.site.register(Permission)
admin.site.unregister(Group)