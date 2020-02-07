from . import constants as c
from django.contrib.contenttypes.models import ContentType
from .models import Manuscript
# Currently For creation of groups with permissions in CoReRe
def populate_models(sender, **kwargs):
    # First we get the out-of-the-box model permissions we will assign to our new groups
    # Note that these permissions define when a group should be able to perform an action on ALL instances of a model
    # The permissions work alongside our object-level permissions that define whether a specific user can access a specific instance of a model
    # For example: editors can add manuscripts but can't view ALL of them. Instead they are assigned view access to the manuscripts they created
    from django.contrib.auth.models import Group
    from django.contrib.auth.models import Permission
    perm_manuscript_add = Permission.objects.get(codename="add_manuscript")
    perm_manuscript_change = Permission.objects.get(codename="change_manuscript")
    perm_manuscript_delete = Permission.objects.get(codename="delete_manuscript")
    perm_manuscript_view = Permission.objects.get(codename="view_manuscript")

    editor, created = Group.objects.get_or_create(name=c.GROUP_ROLE_EDITOR)
    editor.permissions.clear() #First start from nothing
    editor.permissions.add(perm_manuscript_add) 
    # editor.permissions.add(perm_manuscript_change) #Editors are not able to edit 
    # editor.permissions.add(perm_manuscript_delete)
    # editor.permissions.add(perm_manuscript_view)

    author, created = Group.objects.get_or_create(name=c.GROUP_ROLE_AUTHOR)
    author.permissions.clear() #First start from nothing
    #author.permissions.add(perm_manuscript_view)

    verifier, created = Group.objects.get_or_create(name=c.GROUP_ROLE_VERIFIER)
    verifier.permissions.clear() #First start from nothing
    # verifier.permissions.add(perm_manuscript_change) #Should verifiers be able to see anything that isn't assigned at the object level?
    # verifier.permissions.add(perm_manuscript_view)

    curator, created = Group.objects.get_or_create(name=c.GROUP_ROLE_CURATOR)
    curator.permissions.clear() #First start from nothing
    curator.permissions.add(perm_manuscript_add)
    curator.permissions.add(perm_manuscript_change)
    curator.permissions.add(perm_manuscript_delete)
    curator.permissions.add(perm_manuscript_view)
