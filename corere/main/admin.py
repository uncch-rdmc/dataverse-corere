from django.contrib import admin
from .models import Verification, Curation, File, Submission, Manuscript, User
# Register your models here.

admin.site.register(Verification)
admin.site.register(Curation)
admin.site.register(File)
admin.site.register(Submission)
admin.site.register(Manuscript)
admin.site.register(User)