import logging, json, time, requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import constants as c
from corere.main import git as g
from corere.main import docker as d
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns, helper_user_columns
from corere.main.forms import * #TODO: bad practice and I don't use them all
from corere.main.utils import get_pretty_user_list_by_group_prefix
from corere.apps.wholetale import models as wtm
from django.contrib.auth.models import Permission, Group
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from guardian.shortcuts import assign_perm, remove_perm
from corere.main.templatetags.auth_extras import has_group
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import user_passes_test

logger = logging.getLogger(__name__)

def index(request):
    if request.user.is_authenticated:
        if settings.CONTAINER_DRIVER == "wholetale":
            girderToken = request.GET.get("girderToken", None) #provided by wt ouath redirect
            #If no girderToken, we send the user to Whole Tale / Globus to get it.
            if not (girderToken or request.COOKIES.get('girderToken')):
                if request.is_secure():
                    protocol = "https"
                else:
                    protocol = "http"
                    
                r = requests.get(
                    "https://girder."+settings.WHOLETALE_BASE_URL+"/api/v1/oauth/provider",
                    params={"redirect": protocol + "://"+settings.SERVER_ADDRESS+"/?girderToken={girderToken}"} #This is not an f string. The {girderToken} indicates to girder to pass the token back
                )

                response = HttpResponse(content="", status=303)
                response["Location"] = r.json()["Globus"]
                return response

        args = {'user':     request.user, 
                'page_title': _("index_pageTitle"),
                'manuscript_columns':  helper_manuscript_columns(request.user),
                #'submission_columns':  helper_submission_columns(request.user),
                'user_columns':  helper_user_columns(request.user),
                'GROUP_ROLE_EDITOR': c.GROUP_ROLE_EDITOR,
                'GROUP_ROLE_AUTHOR': c.GROUP_ROLE_AUTHOR,
                'GROUP_ROLE_VERIFIER': c.GROUP_ROLE_VERIFIER,
                'GROUP_ROLE_CURATOR': c.GROUP_ROLE_CURATOR,
                'ADD_MANUSCRIPT_PERM_STRING': c.perm_path(c.PERM_MANU_ADD_M)
                }
        response = render(request, "main/index.html", args)
        if girderToken:
            #TODO-WT: If samesite isn't needed we should remove samesite/secure
            response.set_cookie(key="girderToken", value=girderToken, secure=True, samesite='None')
        return response
    else:
        return render(request, "main/login.html")

@login_required
def manuscript_landing(request, id=None):
    manuscript = get_object_or_404(m.Manuscript, id=id)
    # manuscript_avail_buttons = []
    # if(has_transition_perm(manuscript.edit_noop, request.user)):
    #     manuscript_avail_buttons.append('editManuscript')
    #     manuscript_avail_buttons.append('editManuscriptFiles')
    # elif(has_transition_perm(manuscript.view_noop, request.user)):
    #     manuscript_avail_buttons.append('viewManuscript')
    #     manuscript_avail_buttons.append('viewManuscriptFiles')
    # else:
    #     raise Http404()
    # if(has_transition_perm(manuscript.begin, request.user)):
    #     manuscript_avail_buttons.append('progressManuscript')
    # #TODO: add launchNotebook once integration is better
    # # MAD: Should we change these to be transitions?
    # if(not manuscript.is_complete()):
    #     if(request.user.has_any_perm(c.PERM_MANU_ADD_AUTHORS, manuscript)):
    #         manuscript_avail_buttons.append('inviteassignauthor')
    #     if(request.user.has_any_perm(c.PERM_MANU_MANAGE_EDITORS, manuscript)):
    #         manuscript_avail_buttons.append('assigneditor')
    #     if(request.user.has_any_perm(c.PERM_MANU_MANAGE_CURATORS, manuscript)):
    #         manuscript_avail_buttons.append('assigncurator')
    #     if(request.user.has_any_perm(c.PERM_MANU_MANAGE_VERIFIERS, manuscript)):
    #         manuscript_avail_buttons.append('assignverifier')
    # if(has_transition_perm(manuscript.add_submission_noop, request.user)):
    #     manuscript_avail_buttons.append('createSubmission')

    manuscript_author_account_completed = False
    #this logic is a tad confusing. We only populate the completed checkmark if there is one author and they have logged in before
    author_user_set = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id)).user_set.all()
    if(len(author_user_set) == 1):
        for user in author_user_set: #this loop only happens once
            if(user.last_login):
                manuscript_author_account_completed = True
        
    manuscript_authors = get_pretty_user_list_by_group_prefix(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id))
    manuscript_editors = get_pretty_user_list_by_group_prefix(c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(manuscript.id))
    manuscript_curators = get_pretty_user_list_by_group_prefix(c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
    manuscript_verifiers = get_pretty_user_list_by_group_prefix(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))

    #Submission button logic in top button row. Original from datatables.py

    editSubmissionButton = False
    reviewSubmissionButton = False
    generateReportButton = False
    returnSubmissionButton = False
    latest_submission_id = None
    createFirstSubmissionButton = False
    createLaterSubmissionButton = False
    launchContainerCurrentSubButton = False
    submission_count = manuscript.manuscript_submissions.count()

    if has_transition_perm(manuscript.add_submission_noop, request.user) :
        if submission_count < 1 :
            createFirstSubmissionButton = True
        else:
            createLaterSubmissionButton = True
    else:
        try:
            latestSubmission = manuscript.get_latest_submission()
            latest_submission_id = latestSubmission.id

            #TODO: I want a different label for edit/review even if they are the same page in the end

            if (has_transition_perm(latestSubmission.add_edition_noop, request.user)
                or has_transition_perm(latestSubmission.add_curation_noop, request.user)
                or has_transition_perm(latestSubmission.add_verification_noop, request.user)):
                reviewSubmissionButton = True
            else:
                try:
                    if has_transition_perm(latestSubmission.submission_edition.edit_noop, request.user):
                        reviewSubmissionButton = True
                except m.Submission.submission_edition.RelatedObjectDoesNotExist:
                    pass

                try:
                    if has_transition_perm(latestSubmission.submission_curation.edit_noop, request.user):
                        reviewSubmissionButton = True
                except m.Submission.submission_curation.RelatedObjectDoesNotExist:
                    pass

                try:
                    if has_transition_perm(latestSubmission.submission_verification.edit_noop, request.user):
                        reviewSubmissionButton = True
                except m.Submission.submission_verification.RelatedObjectDoesNotExist:
                    pass
            if not reviewSubmissionButton and has_transition_perm(latestSubmission.edit_noop, request.user):
                editSubmissionButton = True
            if has_transition_perm(latestSubmission.send_report, request.user):
                generateReportButton = True
            if has_transition_perm(latestSubmission.finish_submission, request.user):
                returnSubmissionButton = True
            # Similar logic repeated in main page view for showing the sub button for the manuscript level
            if latestSubmission.manuscript.compute_env != 'Other' and settings.CONTAINER_DRIVER == 'wholetale':
                dominant_corere_group = w.get_dominant_group_connector(request.user, latestSubmission).corere_group
                if dominant_corere_group:
                    if dominant_corere_group.name.startswith("Author"):
                        if has_transition_perm(latestSubmission.edit_noop, request.user):
                            launchContainerCurrentSubButton = True
                    else: 
                        if has_transition_perm(latestSubmission.view_noop, request.user):
                            launchContainerCurrentSubButton = True
            else:
                launchContainerCurrentSubButton = True

        except m.Submission.DoesNotExist:
            pass

    args = {'user':     request.user, 
            "latest_submission_id": latest_submission_id, #Will be None if no submissions
            "manuscript_id": id,
            "submission_count": submission_count,
            "manuscript_display_name": manuscript.get_display_name(),
            "manuscript_pub_name": manuscript.pub_name,
            "manuscript_qdr_review": str(manuscript.qdr_review),
            "manuscript_corresponding_author": manuscript.contact_last_name +", "+manuscript.contact_first_name + " ("+manuscript.contact_email+")",
            "manuscript_authors": manuscript_authors,
            "manuscript_author_account_completed": manuscript_author_account_completed,
            "manuscript_editors": manuscript_editors,
            "manuscript_curators": manuscript_curators,
            "manuscript_verifiers": manuscript_verifiers,
            "manuscript_status": manuscript.get__status_display(),
            "manuscript_updated": manuscript.updated_at.strftime("%b %d %Y %H:%M"),
            "manuscript_has_submissions": (manuscript.get_max_submission_version_id() != None),
            "files_dict_list": manuscript.get_gitfiles_pathname(combine=True),
            'submission_columns':  helper_submission_columns(request.user),
            'GROUP_ROLE_EDITOR': c.GROUP_ROLE_EDITOR,
            'GROUP_ROLE_AUTHOR': c.GROUP_ROLE_AUTHOR,
            'GROUP_ROLE_VERIFIER': c.GROUP_ROLE_VERIFIER,
            'GROUP_ROLE_CURATOR': c.GROUP_ROLE_CURATOR,
            # 'manuscript_avail_buttons': json.dumps(manuscript_avail_buttons),
            'ADD_MANUSCRIPT_PERM_STRING': c.perm_path(c.PERM_MANU_ADD_M),
            'page_title': _("manuscript_landing_pageTitle"),
            'create_sub_allowed': str(has_transition_perm(manuscript.add_submission_noop, request.user)).lower,
            'editSubmissionButton': editSubmissionButton,
            'reviewSubmissionButton': reviewSubmissionButton,
            'generateReportButton': generateReportButton,
            'returnSubmissionButton': returnSubmissionButton,
            'createFirstSubmissionButton': createFirstSubmissionButton,
            'createLaterSubmissionButton': createLaterSubmissionButton,
            'launchContainerCurrentSubButton': launchContainerCurrentSubButton
            }

    if settings.CONTAINER_DRIVER == "wholetale":
        args['wholetale'] = True
        try:
            compute_env_str = wtm.ImageChoice.objects.get(wt_id=manuscript.compute_env).name
            args['manuscript_compute_env'] = compute_env_str + " (External)" if compute_env_str == "Other" else compute_env_str
        except wtm.ImageChoice.DoesNotExist:
            pass
    else:
        args['wholetale'] = False
        
    return render(request, "main/manuscript_landing.html", args)

@login_required
def open_notebook(request, id=None):
    #TODO: This needs to be completely rethought. With WholeTale we are allowing previous versions and this doesn't think about that

    manuscript = get_object_or_404(m.Manuscript, id=id)
    if(has_transition_perm(manuscript.edit_noop, request.user)):
        if(not manuscript.get_max_submission_version_id()):
            raise Http404()
        
        latest_submission = manuscript.get_latest_submission()

        if(hasattr(manuscript, 'manuscript_localcontainerinfo')): 
            if manuscript.manuscript_localcontainerinfo.build_in_progress:
                while manuscript.manuscript_localcontainerinfo.build_in_progress:
                    time.sleep(.1)
                    manuscript.manuscript_localcontainerinfo.refresh_from_db()

            elif(latest_submission.files_changed):
                logger.info("Refreshing docker stack (on main page) for manuscript: " + str(manuscript.id))
                d.refresh_notebook_stack(manuscript)
                latest_submission.files_changed = False
                latest_submission.save()
        else:
            logger.info("Building docker stack (on main page) for manuscript: " + str(manuscript.id))
            d.build_manuscript_docker_stack(manuscript, request)
            latest_submission.files_changed = False
            latest_submission.save()

        return redirect(manuscript.manuscript_localcontainerinfo.container_public_address())
    else:
        raise Http404()

@user_passes_test(lambda u: u.is_superuser)
def delete_notebook_stack(request, id=None):
    manuscript = get_object_or_404(m.Manuscript, id=id)
    d.delete_manuscript_docker_stack_crude(manuscript)
    messages.add_message(request, messages.INFO, "Manuscript #"+ str(id) + " notebook stack has been deleted")
    return redirect("/")

@login_required()
def site_actions(request):
    if(has_group(request.user, c.GROUP_ROLE_CURATOR)):
        return render(request, 'main/site_actions.html', {'page_title': "site_actions"})
    else:
        raise Http404()

#NOTE: if we use cookies for session this may no longer be safe
@login_required()
def switch_role(request):
    role_string = request.GET.get('role', '')
    role_full_string = "Role " + role_string
    if(role_string == "Admin"):
        if(request.user.is_superuser):
            request.session['active_role'] = role_string
        else:
            logger.warning("User " + request.user.username + " attempted to switch their active role to admin which they do not have")
    else:
        role = Group.objects.get(name=role_full_string)
        if role in request.user.groups.all():
            request.session['active_role'] = role_string
        else:
            logger.warning("User " + request.user.username + " attempted to switch their active role to a role they do not have ("+ role_full_string +")")
    return redirect(request.GET.get('next', ''))