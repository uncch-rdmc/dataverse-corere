import logging, os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main.forms import * #TODO: bad practice and I don't use them all
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404
from corere.main.utils import fsm_check_transition_perm
#from django.contrib.auth.mixins import LoginRequiredMixin #TODO: Did we need both? I don't think so.
from django.views import View
from corere.main.gitlab import gitlab_repo_get_file_folder_list, helper_get_submission_branch_name, helper_populate_gitlab_files_submission, _helper_generate_gitlab_project_name
#from guardian.decorators import permission_required_or_404

##################### Class based object views #####################
#TODO: move these to own file?
#TODO: "transition_method_name" is a bit misleading. We are (over)using transitions to do perm checks, but the no-ops aren't actually transitioning
#TODO: Test whether I'm leaving open get/post calls on the generic when subclassing.

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
    file_delete_url = None
    helper = GenericFormSetHelper()

    def dispatch(self, request, *args, **kwargs): 
        try:
            self.form = self.form(self.request.POST or None, self.request.FILES or None, instance=self.object)
        except TypeError as e: #Added so that progress and other calls that don't use forms can work. TODO: implement better
            pass
        return super(GenericCorereObjectView, self).dispatch(request,*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url})

    def post(self, request, *args, **kwargs):
        if self.form.is_valid():
            self.form.save() #Note: this is what saves a newly created model instance
            if(self.transition_button_title and request.POST['submit'] == self.transition_button_title): #This checks to see which form button was used. There is probably a more precise way to check
                self.progress_if_allowed(request, *args, **kwargs)
            messages.add_message(request, messages.SUCCESS, self.message)
            return redirect(self.redirect)
        else:
            logger.debug(form.errors)
            #TODO: Pass back form errors
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url})

    ######## Custom class functions. You may want to override some of these. #########

    # To do a tranisition on save. Different transitions are used for each object
    def progress_if_allowed(self, request, *args, **kwargs):
        pass    

class ReadOnlyCorereMixin(object):
    read_only = True
    http_method_names = ['get']
    
#TODO: this needs to be dynamically getting its repo based upon manuscript/submissions
class GitlabFilesMixin(object):
    def dispatch(self, request, *args, **kwargs): 
        if(isinstance(self.object, m.Manuscript)):
            self.repo_dict_list = gitlab_repo_get_file_folder_list(self.object.gitlab_manuscript_id, 'master')
            self.file_delete_url = "/manuscript/"+str(self.object.id)+"/deletefile?file_path="
        elif(isinstance(self.object, m.Submission)):
            self.repo_dict_list = gitlab_repo_get_file_folder_list(self.object.manuscript.gitlab_submissions_id, helper_get_submission_branch_name(self.object.manuscript))
            self.file_delete_url = "/submission/"+str(self.object.id)+"/deletefile?file_path="
        else:
            #print(self.object.__dict__)
            logger.error("Attempted to load Gitlab file for an object which does not have gitlab files")
            #TODO: this should better error that the object provided doesn't have gitlab files
            raise Http404()
        
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

    #TODO: This gets called on every get, do we need to generate the messages this early?
    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('id'):
            self.object = get_object_or_404(self.model, id=kwargs.get('id'))
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' has been updated!'
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
            #TODO: Even if we don't collapse this with progress_if_allowed, we should still refer to it for erroring out in the correct ways
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

    def progress_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.begin, request.user): 
            logger.error("PermissionDenied")
            raise Http404()
        try:
            self.object.begin()
            self.object.save()
        except TransitionNotAllowed as e:
            logger.error("TransitionNotAllowed: " + str(e))
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
    template = 'main/manuscript_super_form.html'
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
#TODO: See if this can be done cleaner
class ManuscriptEditFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    form = ManuscriptFilesForm #TODO: Delete this if we really don't need a form?
    template = 'main/not_form_upload_files.html'
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'git_id': self.object.gitlab_manuscript_id, 'object_title': self.object.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 
            'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master",
            'download_url_p1': os.environ["GIT_LAB_URL"] + "/root/" + self.object.gitlab_manuscript_path + "/-/raw/" + 'master' + "/", 
            'download_url_p2': "?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"]})

#MAD: TOMORROW FIX DOWNLOAD URLS ERRORING ABOVE

#Used for ajax refreshing in EditFiles
class ManuscriptFilesListView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    template = 'main/file_list.html'
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 
            'git_id': self.object.gitlab_manuscript_id, 'object_title': self.object.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name})

class ManuscriptReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, ReadOnlyCorereMixin, GitlabFilesMixin, GenericManuscriptView):
    form = ReadOnlyManuscriptForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'

#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
#This and the other "progressviews" could be made generic, but I get the feeling we'll want to customize all the messaging and then it'll not really be worth it
class ManuscriptProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericManuscriptView):
    #TODO: Should be post
    def get(self, request, *args, **kwargs):
        try:
            self.progress_if_allowed(request, *args, **kwargs)
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was handed to authors!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be handed to authors, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/')

# Do not call directly
class GenericSubmissionView(NotesMixin, GenericCorereObjectView):
    transition_button_title = 'Submit for Review'
    form = SubmissionForm
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission

    def progress_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submit, request.user): 
            logger.debug("PermissionDenied")
            raise Http404()
        try: #TODO: only do this if the reviewer selects a certain form button
            self.object.submit(request.user)
            self.object.save()
        except TransitionNotAllowed as e:
            logger.error("TransitionNotAllowed: " + str(e))
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

#TODO: Do we need the gitlab mixin? probably?
#TODO: Do we need all the parameters being passed?
class SubmissionEditFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    form = GitlabFileFormSet
    template = 'main/form_edit_files.html'
    #template = 'main/not_form_upload_files.html'
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'
    helper=GitlabFileFormSetHelper()

    def get(self, request, *args, **kwargs):
        helper_populate_gitlab_files_submission( self.object.manuscript.gitlab_submissions_id, self.object) #TEST
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'helper':self.helper, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'object_title': "Submission for " + self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":helper_get_submission_branch_name(self.object.manuscript),
            'gitlab_user_token':os.environ["GIT_PRIVATE_ADMIN_TOKEN"]})

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
#TODO: See if this can be done cleaner
class SubmissionUploadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    form = SubmissionUploadFilesForm
    template = 'main/not_form_upload_files.html'
    #For TransitionPermissionMixin
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'notes': self.notes, 'transition_text': self.transition_button_title, 'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'object_title': "Submission for " + self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":helper_get_submission_branch_name(self.object.manuscript),
            'download_url_p1': os.environ["GIT_LAB_URL"] + "/root/" + self.object.manuscript.gitlab_submissions_path + "/-/raw/" + helper_get_submission_branch_name(self.object.manuscript) + "/", 
            'download_url_p2': "?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"]})

#Used for ajax refreshing in EditFiles
class SubmissionFilesListView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    template = 'main/file_list.html'
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'object_title': self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name})

class SubmissionReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, ReadOnlyCorereMixin, GitlabFilesMixin, GenericSubmissionView):
    form = ReadOnlySubmissionForm
    #For TransitionPermissionMixin
    transition_method_name = 'view_noop'

#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
class SubmissionProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionView):
    #TODO: Should be post
    def get(self, request, *args, **kwargs):
        try:
            self.progress_if_allowed(request, *args, **kwargs)
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was handed to curators!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be handed to curators, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/')

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

    def progress_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submission.review, request.user):
            logger.debug("PermissionDenied")
            raise Http404()
        try:
            self.object.submission.review()
            self.object.submission.save()
        except TransitionNotAllowed:
            logger.error("TransitionNotAllowed: " + str(e))
            raise

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

#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
class CurationProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericCurationView):
    #TODO: Should be post
    def get(self, request, *args, **kwargs):
        try:
            self.progress_if_allowed(request, *args, **kwargs)
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was progressed!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be progressed, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/')

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

    def progress_if_allowed(self, request, *args, **kwargs):
        if not fsm_check_transition_perm(self.object.submission.review, request.user):
            logger.debug("PermissionDenied")
            raise Http404()
        try:
            self.object.submission.review()
            self.object.submission.save()
        except TransitionNotAllowed:
            logger.error("TransitionNotAllowed: " + str(e))
            raise

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
    
#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
class VerificationProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericVerificationView):
    #TODO: Should be post
    def get(self, request, *args, **kwargs):
        try:
            self.progress_if_allowed(request, *args, **kwargs)
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was progressed!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be progressed, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/')

################################################################################################