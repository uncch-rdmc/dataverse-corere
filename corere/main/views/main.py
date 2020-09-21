import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import * #TODO: bad practice and I don't use them all
from django.contrib.auth.models import Permission, Group
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404
from django.contrib.auth.decorators import login_required
from corere.main.gitlab import gitlab_delete_file, gitlab_submission_delete_all_files
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
                }
        return render(request, "main/index.html", args)
    else:
        return render(request, "main/login.html")

@login_required
def open_binder(request, id=None):
    manuscript = get_object_or_404(m.Manuscript, id=id)
    if(not request.user.has_any_perm('view_manuscript', manuscript)):
        logger.warning("User id:{0} attempted to launch binder for Manuscript id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
        raise Http404()

    binder_url = binder_build_load(manuscript)
    return redirect(binder_url)
    #print(response.__dict__)

###TODO: There are no perms for notes. I can use the same checks for create as I use to edit sub/cur/ver. For edit/delete implement fsm can_edit.
# What should these permissions even be:
# - Create if you have permission
# - Edit/Delete only if you made it (for now at least)
# I'm not sure if this will work best with multiple "endpoints" or one (see commented code below)

@login_required
def edit_note(request, id=None, edition_id=None, submission_id=None, curation_id=None, verification_id=None):
    if id:
        note = get_object_or_404(m.Note, id=id, parent_edition=edition_id, parent_submission=submission_id, parent_curation=curation_id, parent_verification=verification_id)
        if(not request.user.has_any_perm('change_note', note)):
            logger.warning("User id:{0} attempted to access Note id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
            raise Http404()
        message = 'Your note has been updated!'
        re_url = '../edit'
    else:
        note = m.Note()
        if(edition_id):
            note.parent_edition = get_object_or_404(m.Edition, id=edition_id)
            if(not request.user.has_any_perm('approve_manuscript', note.parent_edition.submission.manuscript)):
            #if(not has_transition_perm(note.parent_edition.edit_noop, request.user)):
                logger.warning("User id:{0} attempted to create a note on edition id:{1} which they had no permission to".format(request.user.id, edition_id))
                raise Http404()
        if(submission_id):
            note.parent_submission = get_object_or_404(m.Submission, id=submission_id)
            if(not request.user.has_any_perm('add_submission_to_manuscript', note.parent_submission.manuscript)):
            #if(not has_transition_perm(note.parent_submission.edit_noop, request.user)):
                logger.warning("User id:{0} attempted to create a note on submission id:{1} which they had no permission to".format(request.user.id, submission_id))
                raise Http404()
        elif(curation_id):
            note.parent_curation = get_object_or_404(m.Curation, id=curation_id)
            if(not request.user.has_any_perm('curate_manuscript', note.parent_curation.submission.manuscript)):
            #if(not has_transition_perm(note.parent_curation.edit_noop, request.user)):
                logger.warning("User id:{0} attempted to create a note on curation id:{1} which they had no permission to".format(request.user.id, curation_id))
                raise Http404()
        elif(verification_id):
            note.parent_verification = get_object_or_404(m.Verification, id=verification_id)
            if(not request.user.has_any_perm('verify_manuscript', note.parent_verification.submission.manuscript)):
            #if(not has_transition_perm(note.parent_verification.edit_noop, request.user)):
                logger.warning("User id:{0} attempted to create a note on verification id:{1} which they had no permission to".format(request.user.id, verification_id))
                raise Http404()
        message = 'Your new note has been created!'
        re_url = './edit'
    form = NoteForm(request.POST or None, request.FILES or None, instance=note)
    if request.method == 'POST': #MAD: Do I need better perms on this?
        if form.is_valid():
            form.save()
            #We go through all available role-groups and add/remove their permissions depending on whether they were selected
            for role in c.get_roles():
                group = Group.objects.get(name=role)
                if role in form.cleaned_data['scope']:
                    assign_perm('view_note', group, note) 
                else:
                    remove_perm('view_note', group, note)           
            return redirect(re_url)
        else:
            #TODO: Return form errors correctly
            logger.debug(form.errors)

    return render(request, 'main/form_create_note.html', {'form': form})

@login_required
def delete_note(request, id=None, edition_id=None, submission_id=None, curation_id=None, verification_id=None):
    if request.method == 'POST':
        note = get_object_or_404(m.Note, id=id, parent_edition=edition_id, parent_submission=submission_id, parent_curation=curation_id, parent_verification=verification_id)
        if(not request.user.has_any_perm('delete_note', note)):
            logger.warning("User id:{0} attempted to delete note id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
            raise Http404()
        note.delete()
        return redirect('../edit')

#TODO: Error if both manuscript and submission id is provided
#TODO: Make this more efficient, I think we could avoid pulling the object itself
@login_required
def delete_file(request, manuscript_id=None, submission_id=None):
    if request.method == 'POST':
        #TODO: Should send the post body
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        if(manuscript_id):
            obj_type = "manuscript"
            obj = get_object_or_404(m.Manuscript, id=manuscript_id) # do we need this or could we have just passed the id?
            git_id = obj.gitlab_manuscript_id
        elif(submission_id):
            obj_type = "submission"
            obj = get_object_or_404(m.Submission, id=submission_id) # do we need this or could we have just passed the id?
            git_id = obj.manuscript.gitlab_submissions_id
        if(not has_transition_perm(obj.edit_noop, request.user)):
            if(manuscript_id):
                logger.warning("User id:{0} attempted to delete gitlab file path:{1} on manuscript id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, manuscript_id))
            else:
                logger.warning("User id:{0} attempted to delete gitlab file path:{1} on submission id:{2} which is either not editable at this point, or they have no permission to".format(request.user.id, file_path, submission_id))
            raise Http404()
        gitlab_delete_file(obj_type, obj, git_id, file_path)

        return redirect('./editfiles') #go to the edit files page again

@login_required
def delete_all_submission_files(request, submission_id):
    if request.method == 'POST':
        submission = get_object_or_404(m.Submission, id=submission_id)
        if(not has_transition_perm(submission.edit_noop, request.user)):
            logger.warning("User id:{0} attempted to delete all gitlab files on manuscript id:{1} which is either not editable at this point, or they have no permission to".format(request.user.id, submission_id))
            raise Http404()
        gitlab_submission_delete_all_files(submission)

        return redirect('./editfiles') #go to the edit files page again

@login_required()
def site_actions(request):
    if(has_group(request.user, c.GROUP_ROLE_CURATOR)):
        return render(request, 'main/site_actions.html')
    else:
        raise Http404()
