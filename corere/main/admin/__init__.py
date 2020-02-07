from django.contrib import admin
from corere.main.models import Verification, Curation, File, Submission, Manuscript, User
from django.contrib.auth.models import Permission, Group
from guardian.admin import GuardedModelAdmin
from .forms import GroupAdminForm#, UserAdminForm

# Register your models here.

admin.site.register(Verification)
admin.site.register(Curation)
admin.site.register(File)
admin.site.register(Submission)
admin.site.register(Manuscript, GuardedModelAdmin)
admin.site.register(User)
#admin.site.register(Permission)

## For using our customized group form
admin.site.unregister(Group)
class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ['permissions']
admin.site.register(Group, GroupAdmin)

## For filtering horizontal on the stock user form
admin.site.unregister(User)
class UserAdmin(admin.ModelAdmin):
    filter_horizontal = ['groups','user_permissions']
admin.site.register(User, UserAdmin)