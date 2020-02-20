from . import constants as c
from django.contrib.contenttypes.models import ContentType
from .models import Manuscript
# Currently For creation of groups with permissions in CoReRe
def populate_models(sender, **kwargs):
    # First we get the out-of-the-box model permissions we will assign to our new groups
    # NOTE: these permissions define when a group should be able to perform an action on ALL instances of a model
    # The permissions work alongside our object-level permissions that define whether a specific user can access a specific instance of a model
    # For example: editors can add manuscripts but can't view ALL of them. Instead they are assigned view access to the manuscripts they created
    from django.contrib.auth.models import Group
    from django.contrib.auth.models import Permission
    perm_manuscript_add = Permission.objects.get(codename="add_manuscript")
    perm_manuscript_change = Permission.objects.get(codename="change_manuscript")
    perm_manuscript_delete = Permission.objects.get(codename="delete_manuscript")
    perm_manuscript_view = Permission.objects.get(codename="view_manuscript")
    perm_manuscript_manage_curators = Permission.objects.get(codename="manage_curators_on_manuscript")
    perm_manuscript_manage_verifiers = Permission.objects.get(codename="manage_verifiers_on_manuscript")
    perm_submission_add = Permission.objects.get(codename="add_submission")
    perm_submission_change = Permission.objects.get(codename="change_submission")
    perm_submission_delete = Permission.objects.get(codename="delete_submission")
    perm_submission_view = Permission.objects.get(codename="view_submission")
    perm_curation_add = Permission.objects.get(codename="add_curation")
    perm_curation_change = Permission.objects.get(codename="change_curation")
    perm_curation_delete = Permission.objects.get(codename="delete_curation")
    perm_curation_view = Permission.objects.get(codename="view_curation")
    perm_verification_add = Permission.objects.get(codename="add_verification")
    perm_verification_change = Permission.objects.get(codename="change_verification")
    perm_verification_delete = Permission.objects.get(codename="delete_verification")
    perm_verification_view = Permission.objects.get(codename="view_verification")

    editor, created = Group.objects.get_or_create(name=c.GROUP_ROLE_EDITOR)
    editor.permissions.clear()
    editor.permissions.add(perm_manuscript_add) 

    author, created = Group.objects.get_or_create(name=c.GROUP_ROLE_AUTHOR)
    author.permissions.clear()

    verifier, created = Group.objects.get_or_create(name=c.GROUP_ROLE_VERIFIER)
    verifier.permissions.clear()

    curator, created = Group.objects.get_or_create(name=c.GROUP_ROLE_CURATOR)
    curator.permissions.clear()
    curator.permissions.add(perm_manuscript_view)
    curator.permissions.add(perm_manuscript_manage_curators)
    curator.permissions.add(perm_manuscript_manage_verifiers)
    curator.permissions.add(perm_manuscript_view)
    curator.permissions.add(perm_submission_view)   
    curator.permissions.add(perm_curation_view)   
    curator.permissions.add(perm_verification_view)   