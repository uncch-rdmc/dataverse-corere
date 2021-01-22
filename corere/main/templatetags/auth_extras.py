from django import template
from django.contrib.auth.models import Group, Permission
from django_fsm import has_transition_perm
from corere.main.models import Manuscript

register = template.Library()

#TODO: Deprecate this? Use perms always?
#      Worth noting that we don't want to check anything object based here currently,
#           we just used these for initial button display and group/perms is good for that
@register.filter(name='has_group')
def has_group(user, group_name): 
    group = Group.objects.get(name=group_name) 
    return True if ((user is not None) and (group in user.groups.all())) else False

@register.filter(name='has_global_perm')
def has_global_perm(user, perm_name):
    return user.has_perm(perm_name)

#TODO: make generalized if we need this function for other objects (e.g. submission)
@register.simple_tag
def manuscript_has_transition_perm(user, obj_id, perm_func_name):
    manuscript = Manuscript.objects.get(id=int(obj_id))
    perm_func = getattr(manuscript, perm_func_name)

    return has_transition_perm(perm_func, user)