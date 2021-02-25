from django import template
register = template.Library()

#The goal for this is to allow variable re-assignment in django templates
#Not best practice, but for our reports page it keeps things simple
@register.simple_tag
def alias(obj):
    """
    Alias Tag
    """
    return obj