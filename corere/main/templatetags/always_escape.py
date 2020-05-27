from django import template
from urllib.parse import quote

register = template.Library()

#The default template escape doesn't seem to act on my url paths, I think because django intuits those should remain
#So I am writing my own that always escapes

@register.filter(name='always_escape')
def always_escape(string):
    """concatenate arg1 & arg2"""
    return quote(string, safe='')