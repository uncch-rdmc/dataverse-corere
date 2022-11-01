from corere.main.admin.admin_base import *
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import AlreadyRegistered
from corere.apps.wholetale import models as wtm
from django.apps import apps
import notifications as notifications

class FullAdminSite(BaseAdminSite):
    site_header = "CORE2 Admin Site Full"
    site_title = "CORE2 Admin Site Full"
    index_title = "Welcome to CORE2 Admin Site"

full_admin_site = FullAdminSite(name='full_admin')

full_admin_site.register(m.Manuscript, GuardedModelAdminCustom)
full_admin_site.register(m.Submission, GuardedModelAdminCustom)
full_admin_site.register(m.Edition, GuardedModelAdminCustom)
full_admin_site.register(m.Curation, GuardedModelAdminCustom)
full_admin_site.register(m.Verification, GuardedModelAdminCustom)
full_admin_site.register(m.Note, GuardedModelAdminCustom)
full_admin_site.register(m.GitFile, GuardedModelAdminCustom)
full_admin_site.register(m.DataverseInstallation, GuardedModelAdminCustom)
# full_admin_site.register(m.VerificationMetadata, GuardedModelAdminCustom)
# full_admin_site.register(m.VerificationMetadataSoftware, GuardedModelAdminCustom)
full_admin_site.register(m.VerificationMetadataBadge, GuardedModelAdminCustom)
full_admin_site.register(m.VerificationMetadataAudit, GuardedModelAdminCustom)

# full_admin_site.unregister(User)
full_admin_site.register(m.User, UserAdmin)
#full_admin_site.unregister(Group)
full_admin_site.register(Group, GroupAdmin)
full_admin_site.register(Permission)

# TODO: If we make the local implementation an app, then this should move
if settings.CONTAINER_DRIVER != "wholetale":
    full_admin_site.register(m.LocalContainerInfo)

full_admin_site.register(m.HistoricalManuscript, HistoryAdmin)
full_admin_site.register(m.HistoricalSubmission, HistoryAdmin)
full_admin_site.register(m.HistoricalEdition, HistoryAdmin)
full_admin_site.register(m.HistoricalCuration, HistoryAdmin)
full_admin_site.register(m.HistoricalVerification, HistoryAdmin)
full_admin_site.register(m.HistoricalUser, HistoryAdmin)
full_admin_site.register(m.HistoricalNote, HistoryAdmin)
# full_admin_site.register(m.HistoricalVerificationMetadata, HistoryAdmin)
# full_admin_site.register(m.HistoricalVerificationMetadataSoftware, HistoryAdmin)
full_admin_site.register(m.HistoricalVerificationMetadataBadge, HistoryAdmin)
full_admin_site.register(m.HistoricalVerificationMetadataAudit, HistoryAdmin)

#Register all models we haven't already registered 
models = apps.get_models()
for model in models:
    try:
        full_admin_site.register(model)
    except AlreadyRegistered:
        pass