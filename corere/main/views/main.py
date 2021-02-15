import logging, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import constants as c
from corere.main import git as g
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import * #TODO: bad practice and I don't use them all
from django.contrib.auth.models import Permission, Group
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from corere.main.binderhub import binder_build_load 
from guardian.shortcuts import assign_perm, remove_perm
from corere.main.templatetags.auth_extras import has_group

logger = logging.getLogger(__name__)

def index(request):
    if request.user.is_authenticated:
        args = {'user':     request.user, 
                'manuscript_columns':  helper_manuscript_columns(request.user),
                'submission_columns':  helper_submission_columns(request.user),
                'GROUP_ROLE_EDITOR': c.GROUP_ROLE_EDITOR,
                'GROUP_ROLE_AUTHOR': c.GROUP_ROLE_AUTHOR,
                'GROUP_ROLE_VERIFIER': c.GROUP_ROLE_VERIFIER,
                'GROUP_ROLE_CURATOR': c.GROUP_ROLE_CURATOR,
                'ADD_MANUSCRIPT_PERM_STRING': c.perm_path(c.PERM_MANU_ADD_M)
                }
        return render(request, "main/index.html", args)
    else:
        return render(request, "main/login.html")

@login_required
def manuscript_landing(request, id=None):
    manuscript = get_object_or_404(m.Manuscript, id=id)
    manuscript_avail_buttons = []
    if(has_transition_perm(manuscript.edit_noop, request.user)):
        manuscript_avail_buttons.append('editManuscript')
        manuscript_avail_buttons.append('editManuscriptFiles')
    elif(has_transition_perm(manuscript.view_noop, request.user)):
        manuscript_avail_buttons.append('viewManuscript')
        manuscript_avail_buttons.append('viewManuscriptFiles')
    if(has_transition_perm(manuscript.begin, request.user)):
        manuscript_avail_buttons.append('progressManuscript')
    #TODO: add launchNotebook once integration is better
    # MAD: Should we change these to be transitions?
    if(not manuscript.is_complete()):
        if(request.user.has_any_perm(c.PERM_MANU_ADD_AUTHORS, manuscript)):
            manuscript_avail_buttons.append('inviteassignauthor')
        if(request.user.has_any_perm(c.PERM_MANU_MANAGE_EDITORS, manuscript)):
            manuscript_avail_buttons.append('assigneditor')
        if(request.user.has_any_perm(c.PERM_MANU_MANAGE_CURATORS, manuscript)):
            manuscript_avail_buttons.append('assigncurator')
        if(request.user.has_any_perm(c.PERM_MANU_MANAGE_VERIFIERS, manuscript)):
            manuscript_avail_buttons.append('assignverifier')
    if(has_transition_perm(manuscript.add_submission_noop, request.user)):
        manuscript_avail_buttons.append('createSubmission')

    print(json.dumps(manuscript_avail_buttons))

    manuscript_authors = list(Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id)).user_set.values_list('username', flat=True))
    manuscript_editors = list(Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(manuscript.id)).user_set.values_list('username', flat=True))
    manuscript_curators = list(Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id)).user_set.values_list('username', flat=True))
    manuscript_verifiers = list(Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id)).user_set.values_list('username', flat=True))

    args = {'user':     request.user, 
            "manuscript_id": id,
            "manuscript_title": manuscript.title,
            "manuscript_authors": manuscript_authors,
            "manuscript_editors": manuscript_editors,
            "manuscript_curators": manuscript_curators,
            "manuscript_verifiers": manuscript_verifiers,
            "manuscript_status": manuscript.get__status_display(),
            'submission_columns':  helper_submission_columns(request.user),
            'GROUP_ROLE_EDITOR': c.GROUP_ROLE_EDITOR,
            'GROUP_ROLE_AUTHOR': c.GROUP_ROLE_AUTHOR,
            'GROUP_ROLE_VERIFIER': c.GROUP_ROLE_VERIFIER,
            'GROUP_ROLE_CURATOR': c.GROUP_ROLE_CURATOR,
            'manuscript_avail_buttons': json.dumps(manuscript_avail_buttons),
            'ADD_MANUSCRIPT_PERM_STRING': c.perm_path(c.PERM_MANU_ADD_M),
            'create_sub_allowed': str(has_transition_perm(manuscript.add_submission_noop, request.user)).lower
            }
    return render(request, "main/manuscript_landing.html", args)

@login_required
def open_binder(request, id=None):
    manuscript = get_object_or_404(m.Manuscript, id=id)
    if(not request.user.has_any_perm(c.PERM_MANU_VIEW_M, manuscript)):
        logger.warning("User id:{0} attempted to launch binder for Manuscript id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
        raise Http404()

    binder_url = binder_build_load(manuscript)
    return redirect(binder_url)

#TODO: Error if both manuscript and submission id is provided
#TODO: Make this more efficient, I think we could avoid pulling the object itself
#This functionality was reused in download_file
@login_required
def delete_file(request, manuscript_id=None, submission_id=None):
    if request.method == 'POST':
        #TODO: Should send the post body
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        #TODO: RE-ENABLE PERMS, we need to get obj before this point
        # if(not has_transition_perm(obj.edit_noop, request.user)):
        #     if(manuscript_id):
        #         logger.warning("User id:{0} attempted to delete gitlab file path:{1} on manuscript id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, manuscript_id))
        #     else:
        #         logger.warning("User id:{0} attempted to delete gitlab file path:{1} on submission id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, submission_id))
        #     raise Http404()
        if(manuscript_id):
            obj_type = "manuscript"
            obj = get_object_or_404(m.Manuscript, id=manuscript_id) # do we need this or could we have just passed the id?
            g.delete_manuscript_file(obj, file_path)
        elif(submission_id):
            obj_type = "submission"
            obj = get_object_or_404(m.Submission, id=submission_id) # do we need this or could we have just passed the id?
            g.delete_submission_file(obj.manuscript, file_path)
            GitFile.objects.get(parent_submission=obj, path=file_path).delete()
        return HttpResponse(status=200)

@login_required
def delete_all_submission_files(request, submission_id):
    if request.method == 'POST':
        submission = get_object_or_404(m.Submission, id=submission_id)
        if(not has_transition_perm(submission.edit_noop, request.user)):
            logger.warning("User id:{0} attempted to delete all gitlab files on manuscript id:{1} which is either not editable at this point, or they have no permission to".format(request.user.id, submission_id))
            raise Http404()
        gitlab_submission_delete_all_files(submission)

        return HttpResponse(status=200)

@login_required
def download_file(request, manuscript_id=None, submission_id=None):
    if request.method == 'GET':

        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        #TODO: RE-ENABLE PERMS, we need to get obj before this point
        #TODO: ALSO REDO ERROR MESSAGES
        # if(not has_transition_perm(obj.view_noop, request.user)):
        #     if(manuscript_id):
        #         logger.warning("User id:{0} attempted to delete gitlab file path:{1} on manuscript id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, manuscript_id))
        #     else:
        #         logger.warning("User id:{0} attempted to delete gitlab file path:{1} on submission id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, submission_id))
        #     raise Http404()
        if(manuscript_id):
            obj_type = "manuscript"
            obj = get_object_or_404(m.Manuscript, id=manuscript_id)
            return g.download_manuscript_file(obj, file_path)
        else:
            obj_type = "submission"
            obj = get_object_or_404(m.Submission, id=submission_id)
            return g.download_submission_file(obj, file_path)

@login_required
def download_all(request, submission_id):
    if request.method == 'GET':
        submission = get_object_or_404(m.Submission, id=submission_id)
        return g.download_all_submission_files(submission)

@login_required()
def site_actions(request):
    if(has_group(request.user, c.GROUP_ROLE_CURATOR)):
        return render(request, 'main/site_actions.html', {'page_header': "site_actions"})
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