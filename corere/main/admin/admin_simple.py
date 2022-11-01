from corere.main.admin.admin_base import *
from django.contrib.admin import AdminSite
from corere.apps.wholetale import models as wtm
import notifications as notifications

class SimpleAdminSite(BaseAdminSite):
    site_header = "CORE2 Admin Site"
    site_title = "CORE2 Admin Site"
    index_title = "Welcome to CORE2 Admin Site"

simple_admin_site = SimpleAdminSite(name='simple_admin')

# TODO: What do we actually want to show in our simple admin?
# - link to sql explorer

# TODO: What do we actually want ediable?
# - DataverseInstallation : Full Access

#Authentication and Authorization
simple_admin_site.register(m.User, UserAdmin)
simple_admin_site.register(Group, GroupAdmin)
simple_admin_site.register(Permission)

#Main (CORE2)
simple_admin_site.register(m.Manuscript, GuardedModelAdminCustom)
simple_admin_site.register(m.Submission, GuardedModelAdminCustom)
simple_admin_site.register(m.Edition, GuardedModelAdminCustom)
simple_admin_site.register(m.Curation, GuardedModelAdminCustom)
simple_admin_site.register(m.Verification, GuardedModelAdminCustom)
simple_admin_site.register(m.Note, GuardedModelAdminCustom)
simple_admin_site.register(m.GitFile, GuardedModelAdminCustom)
simple_admin_site.register(m.DataverseInstallation, GuardedModelAdminCustom)
simple_admin_site.register(m.VerificationMetadataBadge, GuardedModelAdminCustom)
simple_admin_site.register(m.VerificationMetadataAudit, GuardedModelAdminCustom)

# Whole Tale
simple_admin_site.register(wtm.Tale)
simple_admin_site.register(wtm.Instance)
simple_admin_site.register(wtm.GroupConnector)
simple_admin_site.register(wtm.ImageChoice)

#Notifications
simple_admin_site.register(notifications.models.Notification, notifications.admin.NotificationAdmin)