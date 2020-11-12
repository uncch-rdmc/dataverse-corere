import logging, os, requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import forms as f #TODO: bad practice and I don't use them all
from .. import constants as c
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404
from corere.main.utils import fsm_check_transition_perm
#from django.contrib.auth.mixins import LoginRequiredMixin #TODO: Did we need both? I don't think so.
from django.views import View
from corere.main.gitlab import gitlab_repo_get_file_folder_list, helper_get_submission_branch_name, helper_populate_gitlab_files_submission, _helper_generate_gitlab_project_name
logger = logging.getLogger(__name__)  
#from guardian.decorators import permission_required_or_404

########################################## GENERIC + MIXINS ##########################################

#TODO: "transition_method_name" is a bit misleading. We are (over)using transitions to do perm checks, but the no-ops aren't actually transitioning

#To use this at the very least you'll need to use the GetOrGenerateObjectMixin.
class GenericCorereObjectView(View):
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
    repo_dict_list = []
    file_delete_url = None
    #TODO: This is too much. Need a better way to deal with these params. Also some are for manuscript and some are for submission
    helper = f.GenericFormSetHelper()
    page_header = ""
    note_formset = None
    edition_formset = None
    curation_formset = None
    verification_formset = None
    author_formset = None
    data_source_formset = None
    keyword_formset = None 
    note_helper = None
    v_metadata_formset = None
    v_metadata_package_formset = None
    v_metadata_software_formset = None
    v_metadata_badge_formset = None
    v_metadata_audit_formset = None
    create = False #Used by default template

    def dispatch(self, request, *args, **kwargs): 
        try:
            self.form = self.form(self.request.POST or None, self.request.FILES or None, instance=self.object)
        except TypeError as e: #Added so that progress and other calls that don't use forms can work. TODO: implement better
            pass
        return super(GenericCorereObjectView, self).dispatch(request,*args, **kwargs)

    #NOTE: Both get/post has a lot of logic to deal with whether notes are/aren't defined. We should probably handled this in a different way.
    # Maybe find a way to pass the extra import in all the child views, maybe with different templates?

    #The generic get/post is used by submission file views.

    def get(self, request, *args, **kwargs):
        if(isinstance(self.object, m.Manuscript)):
            root_object_title = self.object.title
        else:
            root_object_title = self.object.manuscript.title

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create,
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'page_header': self.page_header, 'root_object_title': root_object_title}

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        print(self.redirect)
        if(isinstance(self.object, m.Manuscript)):
            root_object_title = self.object.title
        else:
            root_object_title = self.object.manuscript.title

        if self.form.is_valid():
            if not self.read_only:
                self.form.save() #Note: this is what saves a newly created model instance
            messages.add_message(request, messages.SUCCESS, self.message)
            return redirect(self.redirect)
        else:
            logger.debug(self.form.errors)

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create,
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'page_header': self.page_header, 'root_object_title': root_object_title}

        return render(request, self.template, context)
    
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
            logger.error("Attempted to load Gitlab file for an object which does not have gitlab files")
            #TODO: this should better error that the object provided doesn't have gitlab files
            raise Http404()
        
        return super(GitlabFilesMixin, self).dispatch(request, *args, **kwargs)

#We need to get the object first before django-guardian checks it.
#For some reason django-guardian doesn't do it in its dispatch and the function it calls does not get the args we need
#Maybe I'm missing something but for now this is the way its happening
#
#Note: this does not save a newly created model in itself, which is good for when we need to check transition perms, etc
class GetOrGenerateObjectMixin(object):
    #TODO: This gets called on every get, do we need to generate the messages this early?
    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('id'):
            self.object = get_object_or_404(self.model, id=kwargs.get('id'))
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' has been updated!'
        elif not self.read_only:
            self.object = self.model()
            if(self.parent_model is not None):
                print("The object create method I didn't want called after create got called")
                setattr(self.object, self.parent_reference_name, get_object_or_404(self.parent_model, id=kwargs.get(self.parent_id_name)))
                if(self.parent_reference_name == "submission"):
                    setattr(self.object, "manuscript", self.object.submission.manuscript)
            self.message = 'Your new '+self.object_friendly_name +' has been created!'
        else:
            logger.error("Error with GetOrGenerateObjectMixin dispatch")
        return super(GetOrGenerateObjectMixin, self).dispatch(request, *args, **kwargs)
    

#A mixin that calls Django fsm has_transition_perm for an object
#It expects that the object has been grabbed already, for example by GetCreateObjectMixin    
#TODO: Is this specifically for noop transitions? if so we should name it that way.
class TransitionPermissionMixin(object):
    transition_on_parent = False
    def dispatch(self, request, *args, **kwargs):
        if(self.transition_on_parent):
            parent_object = getattr(self.object, self.parent_reference_name)
            transition_method = getattr(parent_object, self.transition_method_name)
        else:
            transition_method = getattr(self.object, self.transition_method_name)
        logger.debug("User perms on object: " + str(get_perms(request.user, self.object))) #DEBUG
        if(not has_transition_perm(transition_method, request.user)):
            logger.debug("PermissionDenied")
            raise Http404()
        return super(TransitionPermissionMixin, self).dispatch(request, *args, **kwargs)    
    pass

#via https://gist.github.com/ceolson01/206139a093b3617155a6 , with edits
class GroupRequiredMixin(object):
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

############################################# MANUSCRIPT #############################################

# Do not call directly
class GenericManuscriptView(GenericCorereObjectView):
    object_friendly_name = 'manuscript'
    model = m.Manuscript
    template = 'main/form_object_manuscript.html'

    def get(self, request, *args, **kwargs):
        self.author_formset = f.AuthorManuscriptFormset
        self.data_source_formset = f.DataSourceManuscriptFormset
        self.keyword_formset = f.KeywordManuscriptFormset
        if(isinstance(self.object, m.Manuscript)):
            root_object_title = self.object.title
        else:
            root_object_title = self.object.manuscript.title

        context = {'form': self.form, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 
            'page_header': self.page_header, 'root_object_title': root_object_title, 'helper': self.helper, 'manuscript_helper': f.ManuscriptFormHelper(), 
            'author_inline_helper': f.GenericInlineFormSetHelper(form_id='author'), 'data_source_inline_helper': f.GenericInlineFormSetHelper(form_id='data_source'), 'keyword_inline_helper': f.GenericInlineFormSetHelper(form_id='keyword') }

        if(self.author_formset is not None):
            context['author_formset'] = self.author_formset(instance=self.object, prefix="author_formset")
        if(self.data_source_formset is not None):
            context['data_source_formset'] = self.data_source_formset(instance=self.object, prefix="data_source_formset")
        if(self.keyword_formset is not None):
            context['keyword_formset'] = self.keyword_formset(instance=self.object, prefix="keyword_formset")

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        print(self.redirect)
        self.author_formset = f.AuthorManuscriptFormset
        self.data_source_formset = f.DataSourceManuscriptFormset
        self.keyword_formset = f.KeywordManuscriptFormset
        if(isinstance(self.object, m.Manuscript)):
            root_object_title = self.object.title
        else:
            root_object_title = self.object.manuscript.title

#TODO: IS THIS DOING ANYTHING? CAN IT BE BETTER?
        if(self.author_formset):
            author_formset = self.author_formset(request.POST, instance=self.object, prefix="author_formset")
        if(self.data_source_formset):
            data_source_formset = self.data_source_formset(request.POST, instance=self.object, prefix="data_source_formset")
        if(self.keyword_formset):
            keyword_formset = self.keyword_formset(request.POST, instance=self.object, prefix="keyword_formset")

        if self.form.is_valid():
            if not self.read_only:
                self.form.save() #Note: this is what saves a newly created model instance
                if(self.author_formset):
                    if author_formset.is_valid():
                        author_formset.save()
                if(self.data_source_formset):
                    if data_source_formset.is_valid():
                        data_source_formset.save()
                if(self.keyword_formset):
                    if keyword_formset.is_valid():
                        keyword_formset.save()
            
            messages.add_message(request, messages.SUCCESS, self.message)
            return redirect(self.redirect)
        else:
            logger.debug(self.form.errors)

        context = {'form': self.form, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 
            'page_header': self.page_header, 'root_object_title': root_object_title, 'helper': self.helper, 'manuscript_helper': f.ManuscriptFormHelper(), 
            'author_inline_helper': f.GenericInlineFormSetHelper(form_id='author'), 'data_source_inline_helper': f.GenericInlineFormSetHelper(form_id='data_source'), 'keyword_inline_helper': f.GenericInlineFormSetHelper(form_id='keyword') }

        if(self.author_formset is not None):
            context['author_formset'] = self.author_formset(instance=self.object, prefix="author_formset")
        if(self.data_source_formset is not None):
            context['data_source_formset'] = self.data_source_formset(instance=self.object, prefix="data_source_formset")
        if(self.keyword_formset is not None):
            context['keyword_formset'] = self.keyword_formset(instance=self.object, prefix="keyword_formset")

        return render(request, self.template, context)


#NOTE: LoginRequiredMixin has to be the leftmost. So we have to put it on every "real" view. Yes it sucks.
class ManuscriptCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, PermissionRequiredMixin, GenericManuscriptView):
    form = f.ManuscriptForm
    permission_required = c.perm_path(c.PERM_MANU_ADD_M)
    accept_global_perms = True
    return_403 = True
    page_header = "Create New Manuscript"
    create = True

class ManuscriptEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    form = f.ManuscriptForm
    template = 'main/manuscript_super_form.html'
    transition_method_name = 'edit_noop'
    page_header = "Edit Manuscript"

class ManuscriptReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    form = f.ReadOnlyManuscriptForm
    transition_method_name = 'view_noop'
    page_header = "View Manuscript"
    http_method_names = ['get']
    read_only = True

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS), we just leverage the existing form infrastructure for perm checks etc
class ManuscriptUploadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    form = f.ManuscriptFilesForm #TODO: Delete this if we really don't need a form?
    template = 'main/not_form_upload_files.html'
    transition_method_name = 'edit_noop'
    page_header = "Upload Files for Manuscript"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'git_id': self.object.gitlab_manuscript_id, 'root_object_title': self.object.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 
            'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master", 'page_header': self.page_header,
            'download_url_p1': os.environ["GIT_LAB_URL"] + "/root/" + self.object.gitlab_manuscript_path + "/-/raw/" + 'master' + "/", 
            'download_url_p2': "?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"]})

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS), we just leverage the existing form infrastructure for perm checks etc
#TODO: Pass less parameters, especially token stuff. Could combine with ManuscriptUploadFilesView, but how to handle parameters with that...
class ManuscriptReadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    form = f.ManuscriptFilesForm #TODO: Delete this if we really don't need a form?
    template = 'main/not_form_upload_files.html'
    transition_method_name = 'view_noop'
    page_header = "View Files for Manuscript"
    http_method_names = ['get']
    read_only = True

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'git_id': self.object.gitlab_manuscript_id, 'root_object_title': self.object.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 
            'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master", 'page_header': self.page_header,
            'download_url_p1': os.environ["GIT_LAB_URL"] + "/root/" + self.object.gitlab_manuscript_path + "/-/raw/" + 'master' + "/", 
            'download_url_p2': "?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"]})

class ManuscriptFilesListAjaxView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericManuscriptView):
    template = 'main/file_list.html'
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 'page_header': self.page_header,
            'git_id': self.object.gitlab_manuscript_id, 'root_object_title': self.object.title, 'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name})

#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
#This and the other "progressviews" could be made generic, but I get the feeling we'll want to customize all the messaging and then it'll not really be worth it
class ManuscriptProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericManuscriptView):
    def post(self, request, *args, **kwargs):
        try:
            if not fsm_check_transition_perm(self.object.begin, request.user): 
                print(str(self.object))
                logger.error("PermissionDenied")
                raise Http404()
            try:
                self.object.begin()
                self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was handed to authors!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be handed to authors, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/manuscript/'+str(self.object.id))

############################################# SUBMISSION #############################################

# Do not call directly
class GenericSubmissionView(GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    note_formset = f.NoteSubmissionFormset
    note_helper = f.NoteFormSetHelper()

    def get(self, request, *args, **kwargs):
        self.add_formsets(request)
        root_object_title = self.object.manuscript.title
        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'inline_helper': f.GenericInlineFormSetHelper(),
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'page_header': self.page_header, 'root_object_title': root_object_title,
            'v_metadata_package_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_package'), 'v_metadata_software_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_software'), 'v_metadata_badge_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_badge'), 'v_metadata_audit_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_audit') }
        
        if(self.note_formset is not None):
            context['note_formset'] = self.note_formset(instance=self.object, prefix="note_formset") #TODO: This was set to `= formset`, maybe can delete that variable now?
        if(self.edition_formset is not None):
            context['edition_formset'] = self.edition_formset(instance=self.object, prefix="edition_formset")
        if(self.curation_formset is not None):
            context['curation_formset'] = self.curation_formset(instance=self.object, prefix="curation_formset")
        if(self.verification_formset is not None):
            context['verification_formset'] = self.verification_formset(instance=self.object, prefix="verification_formset")
        if(self.v_metadata_formset is not None):
            context['v_metadata_formset'] = self.v_metadata_formset(instance=self.object, prefix="v_metadata_formset")
        if(self.v_metadata_package_formset is not None):
            context['v_metadata_package_formset'] = self.v_metadata_package_formset(instance=self.object, prefix="v_metadata_package_formset")
        if(self.v_metadata_software_formset is not None):
            context['v_metadata_software_formset'] = self.v_metadata_software_formset(instance=self.object, prefix="v_metadata_software_formset")
        if(self.v_metadata_badge_formset is not None):
            context['v_metadata_badge_formset'] = self.v_metadata_badge_formset(instance=self.object, prefix="v_metadata_badge_formset")
        if(self.v_metadata_audit_formset is not None):
            context['v_metadata_audit_formset'] = self.v_metadata_audit_formset(instance=self.object, prefix="v_metadata_audit_formset")

        if(self.note_helper is not None):
            context['note_helper'] = self.note_helper

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        self.add_formsets(request)
        self.redirect = "/manuscript/"+str(self.object.manuscript.id)

        root_object_title = self.object.manuscript.title

#TODO: IS THIS DOING ANYTHING?
        if(self.note_formset):
            note_formset = self.note_formset(request.POST, instance=self.object, prefix="note_formset")
        if(self.edition_formset):
            edition_formset = self.edition_formset(request.POST, instance=self.object, prefix="edition_formset")
        if(self.curation_formset):
            curation_formset = self.curation_formset(request.POST, instance=self.object, prefix="curation_formset")
        if(self.verification_formset):
            verification_formset = self.verification_formset(request.POST, instance=self.object, prefix="verification_formset")

        if(self.v_metadata_formset):
            v_metadata_formset = self.v_metadata_formset(request.POST, instance=self.object, prefix="v_metadata_formset")
        if(self.v_metadata_package_formset):
            v_metadata_package_formset = self.v_metadata_package_formset(request.POST, instance=self.object, prefix="v_metadata_package_formset")
        if(self.v_metadata_software_formset):
            v_metadata_software_formset = self.v_metadata_software_formset(request.POST, instance=self.object, prefix="v_metadata_software_formset")
        if(self.v_metadata_badge_formset):
            v_metadata_badge_formset = self.v_metadata_badge_formset(request.POST, instance=self.object, prefix="v_metadata_badge_formset")
        if(self.v_metadata_audit_formset):
            v_metadata_audit_formset = self.v_metadata_audit_formset(request.POST, instance=self.object, prefix="v_metadata_audit_formset")

        if self.form.is_valid():
            if not self.read_only:
                self.form.save() #Note: this is what saves a newly created model instance
                if(self.edition_formset):
                    if edition_formset.is_valid():
                        edition_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.curation_formset):
                    if curation_formset.is_valid():
                        curation_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.verification_formset):
                    if verification_formset.is_valid():
                        verification_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.v_metadata_formset):
                    if v_metadata_formset.is_valid():
                        v_metadata_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.v_metadata_package_formset):
                    if v_metadata_package_formset.is_valid():
                        v_metadata_package_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.v_metadata_software_formset):
                    if v_metadata_software_formset.is_valid():
                        v_metadata_software_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.v_metadata_badge_formset):
                    if v_metadata_badge_formset.is_valid():
                        v_metadata_badge_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)
                if(self.v_metadata_audit_formset):
                    if v_metadata_audit_formset.is_valid():
                        v_metadata_audit_formset.save()
                        messages.add_message(request, messages.SUCCESS, self.message)
                    else:
                        logger.debug(self.form.errors)

            if(self.note_formset): #these can be saved even if read only (though I'm not sure our implementation will still use that field anyways)
                if note_formset.is_valid():
                    note_formset.save()
            
            print('submit_progress_submission')
            try:
                if request.POST.get('submit_progress_submission'):
                    if not fsm_check_transition_perm(self.object.submit, request.user): 
                        logger.debug("PermissionDenied")
                        raise Http404()
                    self.object.submit(request.user)
                    self.object.save()
                elif request.POST.get('submit_progress_edition'):
                    if not fsm_check_transition_perm(self.object.submit_edition, request.user):
                        logger.debug("PermissionDenied")
                        raise Http404()
                    self.object.submit_edition()
                    self.object.save()
                elif request.POST.get('submit_progress_curation'):
                    if not fsm_check_transition_perm(self.object.review_curation, request.user):
                        logger.debug("PermissionDenied")
                        raise Http404()
                    self.object.review_curation()
                    self.object.save()
                elif request.POST.get('submit_progress_verification'):
                    if not fsm_check_transition_perm(self.object.review_verification, request.user):
                        logger.debug("PermissionDenied")
                        raise Http404()
                    self.object.review_verification()
                    self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            return redirect(self.redirect)
        else:
            logger.debug(self.form.errors)

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'inline_helper': f.GenericInlineFormSetHelper(),
            'repo_dict_list': self.repo_dict_list, 'file_delete_url': self.file_delete_url, 'page_header': self.page_header, 'root_object_title': root_object_title,
            'v_metadata_package_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_package'), 'v_metadata_software_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_software'), 'v_metadata_badge_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_badge'), 'v_metadata_audit_inline_helper': f.GenericInlineFormSetHelper(form_id='v_metadata_audit') }
        
        if(self.note_formset is not None):
            context['note_formset'] = self.note_formset(instance=self.object, prefix="note_formset") #TODO: This was set to `= formset`, maybe can delete that variable now?
        if(self.edition_formset is not None):
            context['edition_formset'] = self.edition_formset(instance=self.object, prefix="edition_formset")
        if(self.curation_formset is not None):
            context['curation_formset'] = self.curation_formset(instance=self.object, prefix="curation_formset")
        if(self.verification_formset is not None):
            context['verification_formset'] = self.verification_formset(instance=self.object, prefix="verification_formset")
        if(self.v_metadata_formset is not None):
            context['v_metadata_formset'] = self.v_metadata_formset(instance=self.object, prefix="v_metadata_formset")
        if(self.v_metadata_package_formset is not None):
            context['v_metadata_package_formset'] = self.v_metadata_package_formset(instance=self.object, prefix="v_metadata_package_formset")
        if(self.v_metadata_software_formset is not None):
            context['v_metadata_software_formset'] = self.v_metadata_software_formset(instance=self.object, prefix="v_metadata_software_formset")
        if(self.v_metadata_badge_formset is not None):
            context['v_metadata_badge_formset'] = self.v_metadata_badge_formset(instance=self.object, prefix="v_metadata_badge_formset")
        if(self.v_metadata_audit_formset is not None):
            context['v_metadata_audit_formset'] = self.v_metadata_audit_formset(instance=self.object, prefix="v_metadata_audit_formset")

        if(self.note_helper is not None):
            context['note_helper'] = self.note_helper

        return render(request, self.template, context)

    def add_formsets(self, request):
        if(has_transition_perm(self.object.add_edition_noop, request.user)):
            self.edition_formset = f.EditionSubmissionFormset
        else:
            try:
                if(has_transition_perm(self.object.submission_edition.edit_noop, request.user)):
                    self.edition_formset = f.EditionSubmissionFormset
                elif(has_transition_perm(self.object.submission_edition.view_noop, request.user)):
                    self.edition_formset = f.ReadOnlyEditionSubmissionFormset
            except m.Edition.DoesNotExist:
                pass

        if(has_transition_perm(self.object.add_curation_noop, request.user)):
            self.curation_formset = f.CurationSubmissionFormset
        else:
            try:
                if(has_transition_perm(self.object.submission_curation.edit_noop, request.user)):
                    self.curation_formset = f.CurationSubmissionFormset
                elif(has_transition_perm(self.object.submission_curation.view_noop, request.user)):
                    self.curation_formset = f.ReadOnlyCurationSubmissionFormset
            except m.Curation.DoesNotExist:
                pass

        if(has_transition_perm(self.object.add_verification_noop, request.user)):
            self.verification_formset = f.VerificationSubmissionFormset
        else:
            try:
                if(has_transition_perm(self.object.submission_verification.edit_noop, request.user)):
                    self.verification_formset = f.VerificationSubmissionFormset
                elif(has_transition_perm(self.object.submission_verification.view_noop, request.user)):
                    self.verification_formset = f.ReadOnlyVerificationSubmissionFormset
            except m.Verification.DoesNotExist:
                pass

        #TODO: Figure out how we should do perms for these
        self.v_metadata_formset = f.VMetadataSubmissionFormset
        self.v_metadata_package_formset = f.VMetadataPackageVMetadataFormset
        self.v_metadata_software_formset = f.VMetadataSoftwareVMetadataFormset
        self.v_metadata_badge_formset = f.VMetadataBadgeVMetadataFormset
        self.v_metadata_audit_formset = f.VMetadataAuditVMetadataFormset

class SubmissionCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericSubmissionView):
    form = f.SubmissionForm
    transition_method_name = 'add_submission_noop'
    transition_on_parent = True
    page_header = "Create New Submission"
    template = 'main/form_object_submission.html'
    create = True

#Removed TransitionPermissionMixin because multiple cases can edit. We do all the checking inside the view
#TODO: Should we combine this view with the read view? There will be cases where you can edit a review but not the main form maybe?
class SubmissionEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionView):
    form = f.SubmissionForm
    transition_method_name = 'edit_noop'
    page_header = "Edit Submission"
    template = 'main/form_object_submission.html'

class SubmissionReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    form = f.ReadOnlySubmissionForm
    transition_method_name = 'view_noop'
    page_header = "View Submission"
    read_only = True #We still allow post because you can still create/edit notes.
    template = 'main/form_object_submission.html'

#TODO: Do we need the gitlab mixin? probably?
#TODO: Do we need all the parameters being passed? Especially for read?
#TODO: I'm a bit surprised this doesn't blow up when posting with invalid data. The root post is used (I think). Maybe the get is called after to render the page?
class GenericSubmissionFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    template = 'main/form_edit_files_notes.html'
    helper=f.GitlabFileFormSetHelper()
    page_header = "Edit File Metadata for Submission"

    def get(self, request, *args, **kwargs):
        helper_populate_gitlab_files_submission( self.object.manuscript.gitlab_submissions_id, self.object)
        #TODO: Can we just refer to form for everything and delete a bunch of stuff?
        formset = self.form
        
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'root_object_title': self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":helper_get_submission_branch_name(self.object.manuscript),
            'gitlab_user_token':os.environ["GIT_PRIVATE_ADMIN_TOKEN"],'parent':self.object, 'children_formset':formset, 'page_header': self.page_header})

    #Originally copied from GenericCorereObjectView
    def post(self, request, *args, **kwargs):
        formset = self.form
        if formset.is_valid():
            formset.save() #Note: this is what saves a newly created model instance
            messages.add_message(request, messages.SUCCESS, self.message)
            return redirect(self.redirect)
        else:
            logger.debug(formset.errors)

        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'root_object_title': self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":helper_get_submission_branch_name(self.object.manuscript),
            'gitlab_user_token':os.environ["GIT_PRIVATE_ADMIN_TOKEN"],'parent':self.object, 'children_formset':formset, 'page_header': self.page_header})

class SubmissionEditFilesView(GenericSubmissionFilesView):
    transition_method_name = 'edit_noop'
    form = f.GitlabFileNoteFormSet

class SubmissionReadFilesView(GenericSubmissionFilesView):
    transition_method_name = 'view_noop'
    form = f.GitlabReadOnlyFileNoteFormSet
    read_only = True

#No actual editing is done in the form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
#TODO: See if this can be done cleaner
class SubmissionUploadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    form = f.SubmissionUploadFilesForm
    template = 'main/not_form_upload_files.html'
    transition_method_name = 'edit_noop'
    page_header = "Upload Files for Submission"

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'root_object_title': self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":helper_get_submission_branch_name(self.object.manuscript),
            'download_url_p1': os.environ["GIT_LAB_URL"] + "/root/" + self.object.manuscript.gitlab_submissions_path + "/-/raw/" + helper_get_submission_branch_name(self.object.manuscript) + "/", 
            'download_url_p2': "?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"], 'page_header': self.page_header})

#Used for ajax refreshing in EditFiles
class SubmissionFilesListView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitlabFilesMixin, GenericSubmissionView):
    template = 'main/file_list.html'
    transition_method_name = 'edit_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 
            'git_id': self.object.manuscript.gitlab_submissions_id, 'root_object_title': self.object.manuscript.title, 'repo_dict_list': self.repo_dict_list, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, 'page_header': self.page_header})

#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
class SubmissionProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionView):
    def post(self, request, *args, **kwargs):
        print("SUBMISSION PROGRESS")
        print(self.__dict__)
        print(request.__dict__)
        try:
            if not fsm_check_transition_perm(self.object.submit, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            try:
                self.object.submit(request.user)
                self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was handed to the editors for review!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be handed to editors, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/manuscript/'+str(self.object.manuscript.id))

class SubmissionGenerateReportView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionView):
    def post(self, request, *args, **kwargs):
        try:
            if not fsm_check_transition_perm(self.object.generate_report, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            try:
                self.object.generate_report()
                self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was handed to the editors for return!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be handed to editors, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/manuscript/'+str(self.object.manuscript.id))

class SubmissionReturnView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionView):
    def post(self, request, *args, **kwargs):
        try:
            if not fsm_check_transition_perm(self.object.return_submission, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            try:
                self.object.return_submission()
                self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            self.message = 'Your '+self.object_friendly_name + ': ' + str(self.object.id) + ' was returned to the authors!'
            messages.add_message(request, messages.SUCCESS, self.message)
        except (TransitionNotAllowed):
            self.message = 'Object '+self.object_friendly_name + ': ' + str(self.object.id) + ' could not be returned to the authors, please contact the administrator.'
            messages.add_message(request, messages.ERROR, self.message)
        return redirect('/manuscript/'+str(self.object.manuscript.id))