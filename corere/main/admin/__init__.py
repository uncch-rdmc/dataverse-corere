from django.contrib import admin
from corere.main.models import Submission, Edition, Curation, Verification, Manuscript, User, Note, GitFile \
    ,  HistoricalSubmission, HistoricalEdition, HistoricalCuration, HistoricalVerification, HistoricalManuscript, HistoricalUser, HistoricalNote
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
    fields = ('username', 'first_name', 'last_name', 'email', 'invite_key', 'invited_by', 'groups', 'user_permissions', 'is_superuser', 'is_staff', 'is_active', 'date_joined', 'last_login')
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

admin.site.register(Manuscript, GuardedModelAdminCustom)
admin.site.register(Submission, GuardedModelAdminCustom)
admin.site.register(Edition, GuardedModelAdminCustom)
admin.site.register(Curation, GuardedModelAdminCustom)
admin.site.register(Verification, GuardedModelAdminCustom)
admin.site.register(Note, GuardedModelAdminCustom)
admin.site.register(GitFile, GuardedModelAdminCustom)

#admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(Permission)

admin.site.register(HistoricalManuscript, HistoryAdmin)
admin.site.register(HistoricalSubmission, HistoryAdmin)
admin.site.register(HistoricalEdition, HistoryAdmin)
admin.site.register(HistoricalCuration, HistoryAdmin)
admin.site.register(HistoricalVerification, HistoryAdmin)
admin.site.register(HistoricalUser, HistoryAdmin)
admin.site.register(HistoricalNote, HistoryAdmin)