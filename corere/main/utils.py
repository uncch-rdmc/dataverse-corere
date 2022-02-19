import logging
logger = logging.getLogger(__name__)  
from corere.main import constants as c
from corere.main import models as m
from django.http import Http404
from django.contrib.auth.models import Group
#from corere.main.models import Manuscript, User

# For use by the python-social-auth library pipeline.
# With our sign-up flow a user account is created when the user is invited.
# The user is emailed with a one-time url that they use to sign in and provide more info.
# We need to pass this existing user into python-social-auth so it can be associated with the OAuth2 provider.
def social_pipeline_return_session_user(request, **kwargs):
    if(not request.user.is_anonymous):
        kwargs['user'] = request.user
    return kwargs

# This check is a port of the method in django-fsm
# but it removes the other checks so that we can only check permissions first
# This was needed to return the right error depending on whether a user didn't have access vs a transition could not take place
# TODO: Maybe monkey patch this function into django-fsm, overriding the has_transition_perm method (double check its not used internally in fsm)
def fsm_check_transition_perm(bound_method, user):
    """
    Returns True if model in state allows to call bound_method and user have rights on it
    """
    if not hasattr(bound_method, '_django_fsm'):
        im_func = getattr(bound_method, 'im_func', getattr(bound_method, '__func__'))
        raise TypeError('%s method is not transition' % im_func.__name__)

    meta = bound_method._django_fsm
    im_self = getattr(bound_method, 'im_self', getattr(bound_method, '__self__'))
    current_state = meta.field.get_state(im_self)
    
    return (
            #We removed the two below functions because we just want to check the permissions, nothing more
            #meta.has_transition(current_state) and
            #meta.conditions_met(im_self, current_state) and
            meta.has_transition_perm(im_self, current_state, user))

# If the user has the session role for the manuscript, return it
# Otherwise, return a role they do have based on a set order
# Note: This is a bit overloaded with the create logic.
#TODO: This logic doesn't serve the right content when you have multiple roles but not admin
#      But that only happens for testing so turning on admin is fine.
def get_role_name_for_form(user, manuscript, session, create):
    if create:
        if user.is_superuser:
            return "Admin"
        if user.groups.filter(name=c.GROUP_ROLE_EDITOR).exists():
            return "Editor"
        else:
            logger.error("User "+user.username+" requested role name to create a manuscript, when they do not have the group.")
            raise Http404()

    group_base_string = " Manuscript " + str(manuscript.id)
    group_string = session.get("active_role","") + group_base_string

    if "active_role" in session and user.groups.filter(name=group_string).exists():
        return session["active_role"]
    else:
        logger.info("User "+ user.username +" active_role is not available for them on manuscript " + str(manuscript.id) + ". This may be because they have different roles for different manuscripts.")
        if user.is_superuser:
            return "Admin"
        elif user.groups.filter(name="Curator"+group_base_string).exists():
            return "Curator"
        elif user.groups.filter(name="Verifier"+group_base_string).exists():
            return "Verifier"
        elif user.groups.filter(name="Editor"+group_base_string).exists():
            return "Editor"
        elif user.groups.filter(name="Author"+group_base_string).exists():
            return "Author"
        else:
            logger.error("User "+user.username+" requested role for manuscript "+ str(manuscript.id) +" that they have no roles on")
            raise Http404()
    

def get_pretty_user_list_by_group_prefix(group):
    userset = Group.objects.get(name__startswith=group).user_set.all()
    user_list_pretty = []
    for user in userset:
        if(not user.first_name and not user.last_name):
            user_list_pretty += [user.email]
        else:
            user_list_pretty += [user.first_name + ' ' + user.last_name + ' (' +user.email +')']
    return user_list_pretty

#TODO: Write one of these for manuscript? Even there really isn't logic/
def get_progress_bar_html_submission(progress_step_text, submission):
    if(submission._status == m.Submission.Status.NEW or submission._status == m.Submission.Status.REJECTED_EDITOR or submission._status == m.Submission.Status.RETURNED):
        if(submission.manuscript.is_containerized()):
            return generate_progress_bar_html(c.progress_list_container_submission, progress_step_text)
        else:
            return generate_progress_bar_html(c.progress_list_external_submission, progress_step_text)

def generate_progress_bar_html(step_list, last_active_step):
    list_html = '<ol class="progtrckr" data-progtrckr-steps="' + str(len(step_list)) + '">'
    hit_active_step = False

    for step in step_list:
        if step == last_active_step:
            hit_active_step = True
        list_html += '<li class="progtrckr-'+('todo' if hit_active_step else 'done') +'">'+step+'</li>'


    list_html += '</ol>'
    return list_html


# <ol class="progtrckr" data-progtrckr-steps="5">
#     <li class="progtrckr-done">Order Processing</li>
#     <li class="progtrckr-done">Pre-Production</li>
#     <li class="progtrckr-done">In Production</li>
#     <li class="progtrckr-done">Shipped</li>
#     <li class="progtrckr-todo">Delivered</li>
# </ol>