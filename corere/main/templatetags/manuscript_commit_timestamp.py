from django import template
from corere.main.utils import get_newest_manuscript_commit_timestamp

# If our manuscript table starts displaying contents from other tables, we'll need to change how we timestamp for caching
register = template.Library()


@register.simple_tag
def manuscript_commit_timestamp():
    return get_newest_manuscript_commit_timestamp()
