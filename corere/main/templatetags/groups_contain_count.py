from django import template

register = template.Library()
@register.filter
def groups_contain_count(user, group_substring):
    return user.groups.filter(name__contains=group_substring).count()