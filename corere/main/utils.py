import logging

logger = logging.getLogger(__name__)
from corere.main import constants as c
from corere.main import models as m
from django.http import Http404
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.db import connection
from social_core.exceptions import AuthAlreadyAssociated
from social_django.middleware import SocialAuthExceptionMiddleware
from datetime import datetime

# For use by the python-social-auth library pipeline.
# With our sign-up flow a user account is created when the user is invited.
# The user is emailed with a one-time url that they use to sign in and provide more info.
# We need to pass this existing user into python-social-auth so it can be associated with the OAuth2 provider.
def social_pipeline_return_session_user(request, **kwargs):
    if not request.user.is_anonymous:
        kwargs["user"] = request.user
    return kwargs


# This whole middleware process mostly works. The one problem I've run into is that if the user is sent to error (and logged out), they can push the back button, click register again, and it'll work
# I don't really understand why. Going to the url again directly via the email works as expected.
# I'm leaving this as is because the worst that happens is that a user breaks their account and runs into issues using Whole Tale / signing in again.
# Also this may be fixed if I create a middleware to check if logged in globus matches the globus in wholetale their wt_id is for.
class UserAlreadyAssociatedMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if isinstance(exception, AuthAlreadyAssociated):
            return redirect("account_associate_error")


# This check is a port of the method in django-fsm
# but it removes the other checks so that we can only check permissions first
# This was needed to return the right error depending on whether a user didn't have access vs a transition could not take place
# TODO: Maybe monkey patch this function into django-fsm, overriding the has_transition_perm method (double check its not used internally in fsm)
def fsm_check_transition_perm(bound_method, user):
    """
    Returns True if model in state allows to call bound_method and user have rights on it
    """
    if not hasattr(bound_method, "_django_fsm"):
        im_func = getattr(bound_method, "im_func", getattr(bound_method, "__func__"))
        raise TypeError("%s method is not transition" % im_func.__name__)

    meta = bound_method._django_fsm
    im_self = getattr(bound_method, "im_self", getattr(bound_method, "__self__"))
    current_state = meta.field.get_state(im_self)

    return (
        # We removed the two below functions because we just want to check the permissions, nothing more
        # meta.has_transition(current_state) and
        # meta.conditions_met(im_self, current_state) and
        meta.has_transition_perm(im_self, current_state, user)
    )


# If the user has the session role for the manuscript, return it
# Otherwise, return a role they do have based on a set order
# Note: This is a bit overloaded with the create logic.
# TODO: This logic doesn't serve the right content when you have multiple roles but not admin
#      But that only happens for testing so turning on admin is fine.
def get_role_name_for_form(user, manuscript, session, create):
    if create:
        if user.is_superuser:
            return "Admin"
        if user.groups.filter(name=c.GROUP_ROLE_EDITOR).exists():
            return "Editor"
        else:
            logger.error("User " + user.username + " requested role name to create a manuscript, when they do not have the group.")
            raise Http404()

    group_base_string = " Manuscript " + str(manuscript.id)
    group_string = session.get("active_role", "") + group_base_string

    ## Disabled use of session to change form presentation. Its not very useful and causes testing confusion
    # if "active_role" in session and user.groups.filter(name=group_string).exists():
    #     return session["active_role"]
    # else:
    logger.info(
        "User "
        + user.username
        + " active_role is not available for them on manuscript "
        + str(manuscript.id)
        + ". This may be because they have different roles for different manuscripts."
    )
    if user.is_superuser:
        return "Admin"
    elif user.groups.filter(name="Curator" + group_base_string).exists():
        return "Curator"
    elif user.groups.filter(name="Verifier" + group_base_string).exists():
        return "Verifier"
    elif user.groups.filter(name="Editor" + group_base_string).exists():
        return "Editor"
    elif user.groups.filter(name="Author" + group_base_string).exists():
        return "Author"
    else:
        logger.error("User " + user.username + " requested role for manuscript " + str(manuscript.id) + " that they have no roles on")
        raise Http404()


def get_pretty_user_list_by_group_prefix(group):
    userset = Group.objects.get(name__startswith=group).user_set.all()
    user_list_pretty = []
    for user in userset:
        if not user.first_name and not user.last_name:
            user_list_pretty += [user.email]
        else:
            user_list_pretty += [user.first_name + " " + user.last_name + " (" + user.email + ")"]
    return user_list_pretty


# TODO: Write one of these for manuscript? Even there really isn't logic?
# TODO: Maybe switch this to allow passing submission or manuscript, because the cases where we have the sub we don't need to do the manuscript logic
#   ... We could almost get away with just passing submission, but the case where we are creating a sub after the 1st means we need manuscript
def get_progress_bar_html_submission(progress_step_text, manuscript):
    if not manuscript.has_submissions():
        if manuscript.is_containerized():
            return generate_progress_bar_html(c.progress_list_container_submission, progress_step_text)
        else:
            return generate_progress_bar_html(c.progress_list_external_submission, progress_step_text)

    latest_submission = manuscript.get_latest_submission()

    #... this doesn't catch what happens on a new submission after the 1st I think
    if latest_submission._status != m.Submission.Status.RETURNED and latest_submission._status != m.Submission.Status.REJECTED_EDITOR and latest_submission.version_id == 1:
        if manuscript.is_containerized():
            return generate_progress_bar_html(c.progress_list_container_submission, progress_step_text)
        else:
            return generate_progress_bar_html(c.progress_list_external_submission, progress_step_text)
    else:
        if manuscript.is_containerized():
            return generate_progress_bar_html(c.progress_list_container_submission_rejected, progress_step_text)
        else:
            return generate_progress_bar_html(c.progress_list_external_submission_rejected, progress_step_text)

def generate_progress_bar_html(step_list, last_active_step):
    list_html = '<ol class="progtrckr" data-progtrckr-steps="' + str(len(step_list)) + '">'
    hit_active_step = False

    for step in step_list:
        if step == last_active_step:
            hit_active_step = True
            list_html += (
                '<li class="progtrckr-current"><b><span class="progtrckr-text">'
                + step
                + '</span></b><div class="progress-circle-current"></div></li>'
            )
        else:
            if hit_active_step:
                list_html += (
                    '<li class="progtrckr-todo"><span class="progtrckr-text">' + step + '</span><div class="progress-circle-todo"></div></li>'
                )
            else:
                list_html += (
                    '<li class="progtrckr-done"><span class="progtrckr-text">' + step + '</span><div class="progress-circle-done"></div></li>'
                )

    list_html += '<li class="progtrckr-todo"></li>'  # adds an empty bar at the end
    list_html += "</ol>"
    return list_html


def get_newest_manuscript_commit_timestamp():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT max(pg_xact_commit_timestamp(xmin)) FROM main_manuscript")
            row = cursor.fetchone()
        return row[0].timestamp()
    except Exception as e:
        print("exception getting manuscript timestamp. is this a fresh install?")
        print(str(e))
        return (
            datetime.now()
        )  # If this fails (e.g. a fresh manuscript table or flag not set up in psql). This is used for caching so it'll just force a data reload.
