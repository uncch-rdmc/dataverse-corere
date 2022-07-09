from django import template

register = template.Library()

# Convert django message levels to bootstrap alert levels
# TODO: This will not work as expected if passed more than one tag
@register.filter(name="bootstrap_alert_lvl")
def bootstrap_msg_class_lvl(msg_lvl):
    if msg_lvl == "debug":
        return "alert-info"
    if msg_lvl == "info":
        return "alert-info"
    if msg_lvl == "success":
        return "alert-success"
    if msg_lvl == "warning":
        return "alert-warning"
    if msg_lvl == "error":
        return "alert-danger"
    return ""
