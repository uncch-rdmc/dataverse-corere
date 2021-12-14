from django.contrib import admin
from corere.main import models as m
from django.conf import settings
from django.contrib.auth.models import Permission, Group
from guardian.admin import GuardedModelAdminMixin
from simple_history.admin import SimpleHistoryAdmin
from .forms import GroupAdminForm

class GuardedModelAdminCustom(GuardedModelAdminMixin, SimpleHistoryAdmin):
    obj_perms_manage_template = 'main/admin/guardian_obj_perms_manage_custom.html'
    history_list_display = ["history_change_list"]
    pass

class GroupAdmin(SimpleHistoryAdmin):
    form = GroupAdminForm
    filter_horizontal = ['permissions']
    history_list_display = ["history_change_list"]

class UserAdmin(SimpleHistoryAdmin):
    fields = ('username', 'first_name', 'last_name', 'email', 'invited_by', 'groups', 'user_permissions', 'is_superuser', 'is_staff', 'is_active', 'last_oauthproxy_forced_signin', 'date_joined', 'last_login', 'wt_id')
    filter_horizontal = ['groups','user_permissions']
    history_list_display = ["history_change_list"]

#TODO: Improve this display, maybe match individual history list
class HistoryAdmin(admin.ModelAdmin):
    #NOTE: Couldn't add title/last_editor_id as not all models have it. Will fix later
    list_display = ['id', 'history_change_list', 'history_change_reason', 'history_date'] #'title', 'last_editor_id'
    actions = None

    #NOTE: There might be a simpler solution https://stackoverflow.com/questions/49560378/
    def change_view(self, request, object_id=None, form_url='', extra_context=None):
        # use extra_context to disable the other save (and/or delete) buttons
        extra_context = dict(show_save=False, show_save_and_continue=False, show_delete=False)
        # get a reference to the original has_add_permission method
        has_add_permission = self.has_add_permission
        # monkey patch: temporarily override has_add_permission so it returns False
        self.has_add_permission = lambda __: False
        # get the TemplateResponse from super (python 3)
        template_response = super().change_view(request, object_id, form_url, extra_context)
        # restore the original has_add_permission (otherwise we cannot add anymore)
        self.has_add_permission = has_add_permission
        # return the result
        return template_response

admin.site.register(m.Manuscript, GuardedModelAdminCustom)
admin.site.register(m.Submission, GuardedModelAdminCustom)
admin.site.register(m.Edition, GuardedModelAdminCustom)
admin.site.register(m.Curation, GuardedModelAdminCustom)
admin.site.register(m.Verification, GuardedModelAdminCustom)
admin.site.register(m.Note, GuardedModelAdminCustom)
admin.site.register(m.GitFile, GuardedModelAdminCustom)
admin.site.register(m.VerificationMetadata, GuardedModelAdminCustom)
admin.site.register(m.VerificationMetadataSoftware, GuardedModelAdminCustom)
admin.site.register(m.VerificationMetadataBadge, GuardedModelAdminCustom)
admin.site.register(m.VerificationMetadataAudit, GuardedModelAdminCustom)

#admin.site.unregister(User)
admin.site.register(m.User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(Permission)

#TODO: If we make the local implementation an app, then this should move
if settings.CONTAINER_DRIVER != 'wholetale' :
    admin.site.register(m.LocalContainerInfo)

admin.site.register(m.HistoricalManuscript, HistoryAdmin)
admin.site.register(m.HistoricalSubmission, HistoryAdmin)
admin.site.register(m.HistoricalEdition, HistoryAdmin)
admin.site.register(m.HistoricalCuration, HistoryAdmin)
admin.site.register(m.HistoricalVerification, HistoryAdmin)
admin.site.register(m.HistoricalUser, HistoryAdmin)
admin.site.register(m.HistoricalNote, HistoryAdmin)
admin.site.register(m.HistoricalVerificationMetadata, HistoryAdmin)
admin.site.register(m.HistoricalVerificationMetadataSoftware, HistoryAdmin)
admin.site.register(m.HistoricalVerificationMetadataBadge, HistoryAdmin)
admin.site.register(m.HistoricalVerificationMetadataAudit, HistoryAdmin)




