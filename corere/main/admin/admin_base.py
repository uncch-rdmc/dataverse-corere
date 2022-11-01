#General initialization inherited by the two admin sites

from django.shortcuts import render

from django.contrib import admin
from corere.main import models as m
from django.conf import settings
from django.contrib.auth.models import Permission, Group
from guardian.admin import GuardedModelAdminMixin
from simple_history.admin import SimpleHistoryAdmin
from django.urls import path
from .forms import GroupAdminForm

class BaseAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('test/<int:id>', self.admin_view(self.test_view) , name='recipecalc'),
        ]
        return custom_urls + urls
    
    def test_view(self, request, id):
        context = {
            "has_permission": True, #Shows username header text. TODO: We are leveraging other user checks via "admin_view", so setting this true this is ok?
            "title": "A fun test"
        }  
        return render(request, "admin/custom_test.html", context)

class GuardedModelAdminCustom(GuardedModelAdminMixin, SimpleHistoryAdmin):
    obj_perms_manage_template = "admin/guardian_obj_perms_manage_custom.html"
    history_list_display = ["history_change_list"]
    pass


class GroupAdmin(SimpleHistoryAdmin):
    form = GroupAdminForm
    filter_horizontal = ["permissions"]
    history_list_display = ["history_change_list"]


class UserAdmin(SimpleHistoryAdmin):
    fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "invited_by",
        "groups",
        "user_permissions",
        "is_superuser",
        "is_staff",
        "is_active",
        "last_oauthproxy_forced_signin",
        "date_joined",
        "last_login",
        "wt_id",
    )
    filter_horizontal = ["groups", "user_permissions"]
    history_list_display = ["history_change_list"]


# TODO: Improve this display, maybe match individual history list
class HistoryAdmin(admin.ModelAdmin):
    # NOTE: Couldn't add title/last_editor_id as not all models have it. Will fix later
    list_display = ["id", "history_change_list", "history_change_reason", "history_date"]  #'title', 'last_editor_id'
    actions = None

    # NOTE: There might be a simpler solution https://stackoverflow.com/questions/49560378/
    def change_view(self, request, object_id=None, form_url="", extra_context=None):
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
