from . import constants as c
from django.contrib.contenttypes.models import ContentType
from corere.main import models as m
from django.contrib.auth import get_user_model
#from .models import Manuscript

# Currently For creation of groups with permissions in CORE2

# First we get the out-of-the-box model permissions we will assign to our new groups
# NOTE: these permissions define when a group should be able to perform an action on ALL instances of a model
# The permissions work alongside our object-level permissions that define whether a specific user can access a specific instance of a model
# For example: editors can add manuscripts but can't view ALL of them. Instead they are assigned view access to the manuscripts they created
def populate_models(sender, **kwargs):
    from django.contrib.auth.models import Group
    from django.contrib.auth.models import Permission
    perm_manuscript_add = Permission.objects.get(codename=c.PERM_MANU_ADD_M)
    # perm_manuscript_change = Permission.objects.get(codename=c.PERM_MANU_CHANGE_M)
    # perm_manuscript_change_files = Permission.objects.get(codename=c.PERM_MANU_CHANGE_M_FILES)
    #perm_manuscript_delete = Permission.objects.get(codename=c.PERM_MANU_DELETE_M)
    perm_manuscript_view = Permission.objects.get(codename=c.PERM_MANU_VIEW_M)

    perm_manuscript_add_authors = Permission.objects.get(codename=c.PERM_MANU_ADD_AUTHORS)
    perm_manuscript_remove_authors = Permission.objects.get(codename=c.PERM_MANU_REMOVE_AUTHORS)
    perm_manuscript_manage_editors = Permission.objects.get(codename=c.PERM_MANU_MANAGE_EDITORS)
    perm_manuscript_manage_curators = Permission.objects.get(codename=c.PERM_MANU_MANAGE_CURATORS)
    perm_manuscript_manage_verifiers = Permission.objects.get(codename=c.PERM_MANU_MANAGE_VERIFIERS)

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
    curator.permissions.add(perm_manuscript_add_authors)
    curator.permissions.add(perm_manuscript_remove_authors)
    curator.permissions.add(perm_manuscript_manage_editors)
    curator.permissions.add(perm_manuscript_manage_curators)
    curator.permissions.add(perm_manuscript_manage_verifiers)

    ## Add all roles to superusers 

    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True)

    for user in superusers:
        for role in c.get_roles():
            my_group = Group.objects.get(name=role) 
            my_group.user_set.add(user)