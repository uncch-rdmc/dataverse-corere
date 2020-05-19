import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import constants as c
from corere.main.views.datatables import helper_manuscript_columns, helper_submission_columns
from corere.main.forms import * #bad practice but I use them all...
from django.contrib.auth.models import Permission, Group
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_fsm import can_proceed, has_transition_perm, TransitionNotAllowed
from django.core.exceptions import FieldDoesNotExist #,PermissionDenied
from django.http import Http404
from corere.main.utils import fsm_check_transition_perm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views import View
from corere.main.gitlab import gitlab_repo_get_file_folder_list
#from guardian.decorators import permission_required_or_404

logger = logging.getLogger(__name__)

def index(request):
    if request.user.is_authenticated:
        if(request.user.invite_key): #user hasn't finished signing up if we are still holding their key
            return redirect("/account_user_details")
        else:
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

#To use this at the very least you'll need to use the GetOrGenerateObjectMixin.
class GenericCorereObjectView(View):
    transition_button_title = None
    form = None
    model = None
    template = 'main/form_object_generic.html'
    redirect = '/'
    read_only = False
    message = None
    http_method_names = ['get', 'post'] #Used by the base View class
    #For GetOrGenerateObjectMixin, instantiated here so they don't override.
    parent_reference_name = None
    parent_id_name = None
    parent_model = None
    #TODO: Move definitions into mixins? Will that blow up?
    #NOTE: that these do not clear on their own and have to be cleared manually. There has to be a better way...
    #      If you don't clear them you get duplicate notes etc
    notes = [] 
    repo_dict_list = []

    def dispatch(self, request, *args, **kwargs): 
        self.form = self.form(self.request.POST or None, self.request.FILES or None, instance=self.object)
        return super(GenericCorereObjectView, self).dispatch(request,*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'repo_dict_list': self.repo_dict_list})

    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.form.save() #Note: this is what saves a newly created model instance
            if(self.transition_button_title and request.POST['submit'] == self.transition_button_title): #This checks to see which form button was used. There is probably a more precise way to check
                self.transition_if_allowed(request, *args, **kwargs)
            messages.add_message(request, messages.INFO, self.message)
            return redirect(self.redirect)
        else:
            logger.debug(form.errors) #Handle exception better
        return render(request, self.template, {'form': self.form, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'repo_dict_list': self.repo_dict_list})

    ######## Custom class functions. You may want to override some of these. #########

    # To do a tranisition on save. Different transitions are used for each object
    def transition_if_allowed(self, request, *args, **kwargs):
        pass    

class ReadOnlyCorereMixin(object):
    read_only = True
    http_method_names = ['get']
    
class GitlabFilesMixin(object):
    def dispatch(self, request, *args, **kwargs): 
        self.repo_dict_list = gitlab_repo_get_file_folder_list(self.object)
        return super(GitlabFilesMixin, self).dispatch(request, *args, **kwargs)

class NotesMixin(object):
    def dispatch(self, request, *args, **kwargs): 
        # try:
        self.model._meta.get_field('notes')
        self.notes = []
        for note in self.object.notes.all():
            if request.user.has_perm('view_note', note):
                self.notes.append(note)
            else:
                logger.debug("user did not have permission for note: " + note.text)
        # except FieldDoesNotExist: #To catch models without notes (Manuscript)
        #     pass
        return super(NotesMixin, self).dispatch(request, *args, **kwargs)

#We need to get the object first before django-guardian checks it.
#For some reason django-guardian doesn't do it in its dispatch and the function it calls does not get the args we need
#Maybe I'm missing something but for now this is the way its happening
#
#Note: this does not save a newly created model in itself, which is good for when we need to check transition perms, etc
class GetOrGenerateObjectMixin(object):
    #TODO: Should this be instantiated?
    #object_friendly_name = None

    #Instantiated in GenericCorereObjectView
    # parent_reference_name = None
    # parent_id_name = None
    # parent_model = None

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('id'):
            self.object = get_object_or_404(self.model, id=kwargs.get('id'))
            self.message = 'Your '+self.object_friendly_name +' has been updated!'
        elif not self.read_only: #kwargs.get(self.parent_id_name) and 
            self.object = self.model()
            if(self.parent_model is not None):
                setattr(self.object, self.parent_reference_name, get_object_or_404(self.parent_model, id=kwargs.get(self.parent_id_name)))
            self.message = 'Your new '+self.object_friendly_name +' has been created!'
        else:
            logger.error("Error with GetOrGenerateObjectMixin dispatch")
        return super(GetOrGenerateObjectMixin, self).dispatch(request, *args, **kwargs)
    

#A mixin that calls Django fsm has_transition_perm for an object
#It expects that the object has been grabbed already, for example by GetCreateObjectMixin    
#TODO: Is this specifically for noop transitions? if so we should name it that way.
class TransitionPermissionMixin(object):
    #TODO: Should this be instantiated?
    transition_method_name = None
    transition_on_parent = False
    def dispatch(self, request, *args, **kwargs):
        if(self.transition_on_parent):
            parent_object = getattr(self.object, self.parent_reference_name)
            transition_method = getattr(parent_object, self.transition_method_name)
        else:
            transition_method = getattr(self.object, self.transition_method_name)
        logger.debug("User perms on object: " + str(get_perms(request.user, self.object))) #DEBUG
        if(not has_transition_perm(transition_method, request.user)):
            #TODO: Even if we don't collapse this with transition_if_allowed, we should still refer to it for erroring out in the correct ways
            logger.debug("PermissionDenied")
            raise Http404()
        return super(TransitionPermissionMixin, self).dispatch(request, *args, **kwargs)    
    pass

#via https://gist.github.com/ceolson01/206139a093b3617155a6 , with edits
class GroupRequiredMixin(object):
    """ group_required - list of strings """
    #TODO: Should this be instantiated?
    #groups_required = []

    def dispatch(self, request, *args, **kwargs):
        if(len(self.groups_required)>0):
            if not request.user.is_authenticated:
                raise Http404()
            else:
                user_groups = []
                for group in request.user.groups.values_list('name', flat=True):
                    user_groups.append(group)
                if len(set(user_groups).intersection(self.groups_required)) <= 0:
                    raise Http404()
        return super(GroupRequiredMixin, self).dispatch(request, *args, **kwargs)

################################################################################################

# Do not call directly
class GenericManuscriptView(GenericCorereObjectView):
    transition_button_title = 'Save and Assign to Authors'
    object_friendly_name = 'manuscript'
    model = m.Manuscript

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.begin, request.user): 
            logger.debug("PermissionDenied")
            raise Http404()
        try: #TODO: only do this if the reviewer selects a certain form button
            self.object.begin()
            self.object.save()
        except TransitionNotAllowed as e:
            logger.debug("TransitionNotAllowed: " + str(e)) #Handle exception better
            raise

#NOTE: LoginRequiredMixin has to be the leftmost. So we have to put it on every "real" view. Yes it sucks.
class ManuscriptCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, PermissionRequiredMixin, GenericManuscriptView):
    form = ManuscriptForm
    #groups_required = [c.GROUP_ROLE_EDITOR] #For GroupRequiredMixin
    #For PermissionRequiredMixin
    permission_required = "main.add_manuscript"
    accept_global_perms = True
    return_403 = True

class ManuscriptEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    form = ManuscriptForm
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
#TODO: See if this can be done cleaner
class ManuscriptEditFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    form = ManuscriptFilesForm
    template = 'main/not_form_upload_files.html'
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'manuscript_git_id': self.object.gitlab_id, 'manuscript_title': self.object.title, 'repo_dict_list': self.repo_dict_list})

class ManuscriptReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, ReadOnlyCorereMixin, GitlabFilesMixin, GenericManuscriptView):
    form = ReadOnlyManuscriptForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'


    
# Do not call directly
class GenericSubmissionView(NotesMixin, GenericCorereObjectView):
    transition_button_title = 'Submit for Review'
    form = SubmissionForm
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submit, request.user): 
            logger.debug("PermissionDenied")
            raise Http404()
        try: #TODO: only do this if the reviewer selects a certain form button
            self.object.submit(request.user)
            self.object.save()
        except TransitionNotAllowed as e:
            logger.debug("TransitionNotAllowed: " + str(e)) #Handle exception better
            raise

class SubmissionCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericSubmissionView):
    form = SubmissionForm
    #For TransitionPermissionMixin
    transition_method_name = 'add_submission_noop'
    transition_on_parent = True

class SubmissionEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericSubmissionView):
    form = SubmissionForm
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

class SubmissionReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, ReadOnlyCorereMixin, GenericSubmissionView):
    form = ReadOnlySubmissionForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'

# Do not call directly
class GenericCurationView(NotesMixin, GenericCorereObjectView):
    transition_button_title = 'Submit and Progress'
    form = CurationForm
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_model = m.Submission
    object_friendly_name = 'curation'
    model = m.Curation
    redirect = '/'

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submission.review, request.user):
            logger.debug("PermissionDenied")
            raise Http404()
        try:
            self.object.submission.review()
            self.object.submission.save()
        except TransitionNotAllowed:
            pass #We do not do review if the statuses don't align

class CurationCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCurationView):
    form = CurationForm
    #For TransitionPermissionMixin
    transition_method_name = 'add_curation_noop'
    transition_on_parent = True

class CurationEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCurationView):
    form = CurationForm
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

class CurationReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin,  ReadOnlyCorereMixin, GenericCurationView):
    form = ReadOnlyCurationForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'

# Do not call directly
class GenericVerificationView(NotesMixin, GenericCorereObjectView):
    transition_button_title = 'Submit and Progress'
    form = VerificationForm
    parent_reference_name = 'submission'
    parent_id_name = "submission_id"
    parent_model = m.Submission
    object_friendly_name = 'verification'
    model = m.Verification
    redirect = '/'

    def transition_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submission.review, request.user):
            logger.debug("PermissionDenied")
            raise Http404()
        try:
            self.object.submission.review()
            self.object.submission.save()
        except TransitionNotAllowed:
            pass #We do not do review if the statuses don't align

class VerificationCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericVerificationView):
    form = VerificationForm
    #For TransitionPermissionMixin
    transition_method_name = 'add_verification_noop'
    transition_on_parent = True

class VerificationEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin,  GenericVerificationView):
    form = VerificationForm
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

class VerificationReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, ReadOnlyCorereMixin, GenericVerificationView):
    form = ReadOnlyVerificationForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'
    

################################################################################################


###TODO: There are no perms for notes. I can use the same checks for create as I use to edit sub/cur/ver. For edit/delete implement fsm can_edit.
# What should these permissions even be:
# - Create if you have permission
# - Edit/Delete only if you made it (for now at least)
# I'm not sure if this will work best with multiple "endpoints" or one (see commented code below)

@login_required
def edit_note(request, id=None, submission_id=None, curation_id=None, verification_id=None):
    if id:
        note = get_object_or_404(m.Note, id=id, parent_submission=submission_id, parent_curation=curation_id, parent_verification=verification_id)
        if(not request.user.has_perm('view_note', note)):
            logger.warning("User id:{0} attempted to access Note id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
            raise Http404()
        message = 'Your note has been updated!'
        re_url = '../edit'
    else:
        note = m.Note()
        if(submission_id):
            note.parent_submission = get_object_or_404(m.Submission, id=submission_id)
            if(not request.user.has_perm('add_submission_to_manuscript', note.parent_submission.manuscript)):
                logger.warning("User id:{0} attempted to create a note on submission id:{1} which they had no permission to".format(request.user.id, submission_id))
                raise Http404()
        elif(curation_id):
            note.parent_curation = get_object_or_404(m.Curation, id=curation_id)
            if(not request.user.has_perm('curate_manuscript', note.parent_curation.submission.manuscript)):
                logger.warning("User id:{0} attempted to create a note on curation id:{1} which they had no permission to".format(request.user.id, curation_id))
                raise Http404()
        elif(verification_id):
            note.parent_verification = get_object_or_404(m.Verification, id=verification_id)
            if(not request.user.has_perm('verify_manuscript', note.parent_verification.submission.manuscript)):
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
            logger.debug(form.errors) #Handle exception better

    return render(request, 'main/form_create_note.html', {'form': form})

@login_required
def delete_note(request, id=None, submission_id=None, curation_id=None, verification_id=None):
    note = get_object_or_404(m.Note, id=id, parent_submission=submission_id, parent_curation=curation_id, parent_verification=verification_id)
    if(not request.user.has_perm('delete_note', note)):
        logger.warning("User id:{0} attempted to delete note id:{1} which they had no permission to and should not be able to see".format(request.user.id, id))
        raise Http404()
    note.delete()
    return redirect('../edit')