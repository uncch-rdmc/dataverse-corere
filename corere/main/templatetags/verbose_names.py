from django import template

register = template.Library()


@register.simple_tag
def get_verbose_field_name(instance, field_name):
    """
    Returns verbose_name for a field.
    Via: https://stackoverflow.com/questions/14496978/
    """
    return instance._meta.get_field(field_name).verbose_name.title()
