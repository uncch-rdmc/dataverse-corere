from django.contrib import admin
from .models import Verification, Curation, File, Submission, Manuscript, User
from django.contrib.auth.models import Permission
# Register your models here.

admin.site.register(Verification)
admin.site.register(Curation)
admin.site.register(File)
admin.site.register(Submission)
admin.site.register(Manuscript)
admin.site.register(User)
admin.site.register(Permission) #MAD: Testing whether we want this enabled