from django import template
from corere.main import constants as c

register = template.Library()
@register.filter
def groups_contain_count_no_completed(user, group_substring):
    return user.groups.filter(name__contains=group_substring).exclude(name__endswith=c.GROUP_COMPLETED_SUFFIX).count()