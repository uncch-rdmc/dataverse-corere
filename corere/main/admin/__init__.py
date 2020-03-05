from django.contrib import admin
from corere.main.models import Verification, Curation, File, Submission, Manuscript, User, Note
from django.contrib.auth.models import Permission, Group
from guardian.admin import GuardedModelAdmin
from .forms import GroupAdminForm

class GuardedModelAdminCustom(GuardedModelAdmin):
    obj_perms_manage_template = 'main/admin/guardian_obj_perms_manage_custom.html'
    pass

class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ['permissions']

class UserAdmin(admin.ModelAdmin):
    fields = ('username', 'first_name', 'last_name', 'email', 'invite_key', 'invited_by', 'groups', 'user_permissions', 'is_superuser', 'is_staff', 'is_active', 'date_joined', 'last_login')
    filter_horizontal = ['groups','user_permissions']

admin.site.register(Verification, GuardedModelAdminCustom)
admin.site.register(Curation, GuardedModelAdminCustom)
admin.site.register(File)
admin.site.register(Note, GuardedModelAdminCustom)
admin.site.register(Submission, GuardedModelAdminCustom)
admin.site.register(Manuscript, GuardedModelAdminCustom)
#admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(Permission)