import logging, os, requests, urllib, time, git, sseclient, threading, base64, json, tempfile
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from corere.main import models as m
from corere.main import forms as f #TODO: bad practice and I don't use them all
from corere.main import docker as d
from corere.main import wholetale_corere as w
from corere.main import dataverse as dv
from corere.apps.wholetale import models as wtm
from corere.main import git as g
from .. import constants as c 
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from guardian.mixins import LoginRequiredMixin, PermissionRequiredMixin
from guardian.core import ObjectPermissionChecker
from django_fsm import has_transition_perm, TransitionNotAllowed
from django.http import Http404
from corere.main.utils import fsm_check_transition_perm, get_role_name_for_form, get_progress_bar_html_submission, generate_progress_bar_html
from django.contrib.auth.models import Group
#from django.contrib.auth.mixins import LoginRequiredMixin #TODO: Did we need both? I don't think so.
from django.views import View
from corere.main import git as g
from django.http import HttpResponse, StreamingHttpResponse
from django.db.models import Max
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.translation import gettext as _
from notifications.signals import notify
from templated_email import send_templated_mail
from django.utils.datastructures import MultiValueDictKeyError
from django.db import transaction
from django_renderpdf.views import PDFView

logger = logging.getLogger(__name__)  

#from guardian.decorators import permission_required_or_404

########################################## GENERIC + MIXINS ##########################################

#TODO: "transition_method_name" is a bit misleading. We are (over)using transitions to do perm checks, but the no-ops aren't actually transitioning

#To use this at the very least you'll need to use the GetOrGenerateObjectMixin.
class GenericCorereObjectView(View):
    form = None
    form_dict = None
    model = None
    template = 'main/form_object_generic.html'
    redirect = '..'
    read_only = False
    msg = None
    http_method_names = ['get', 'post'] #Used by the base View class
    #For GetOrGenerateObjectMixin, instantiated here so they don't override.
    parent_reference_name = None
    parent_id_name = None
    parent_model = None
    #TODO: Move definitions into mixins? Will that blow up?
    #NOTE: that these do not clear on their own and have to be cleared manually. There has to be a better way...
    #      If you don't clear them you get duplicate notes etc
    files_dict_list = []
    file_delete_url = None
    #TODO: This is too much. Need a better way to deal with these params. Also some are for manuscript and some are for submission
    helper = f.GenericFormSetHelper()
    page_title = ""
    page_help_text = None
    note_formset = None
    note_helper = None
    
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
            manuscript_display_name = self.object.get_display_name()
        else:
            manuscript_display_name = self.object.manuscript.get_display_name()

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create,
            'page_title': self.page_title, 'page_help_text': self.page_help_text, 'manuscript_display_name': manuscript_display_name}

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        print(self.redirect)
        if(isinstance(self.object, m.Manuscript)):
            manuscript_display_name = self.object.get_display_name()
        else:
            manuscript_display_name = self.object.manuscript.get_display_name()

        if self.form.is_valid():
            if not self.read_only:
                self.form.save() #Note: this is what saves a newly created model instance
            messages.add_message(request, messages.SUCCESS, self.msg)
            return redirect(self.redirect)
        else:
            logger.debug(self.form.errors)

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create,
            'page_title': self.page_title, 'page_help_text': self.page_help_text, 'manuscript_display_name': manuscript_display_name}

        return render(request, self.template, context)

class GitFilesMixin(object):
    def setup(self, request, *args, **kwargs):
        self.files_dict_list = self.object.get_gitfiles_pathname(combine=True)

        if(isinstance(self.object, m.Manuscript)):
            self.file_delete_url = "/manuscript/"+str(self.object.id)+"/deletefile/?file_path="
            self.file_download_url = "/manuscript/"+str(self.object.id)+"/downloadfile/?file_path="
        elif(isinstance(self.object, m.Submission)):
            self.file_delete_url = "/submission/"+str(self.object.id)+"/deletefile/?file_path="
            self.file_download_url = "/submission/"+str(self.object.id)+"/downloadfile/?file_path="
            print(self.file_download_url)
        else:
            logger.error("Attempted to load Git file for an object which does not have git files") #TODO: change error
            raise Http404()

        return super(GitFilesMixin, self).setup(request, *args, **kwargs)

#We need to get the object first before django-guardian checks it.
#For some reason django-guardian doesn't do it in its dispatch and the function it calls does not get the args we need
#Maybe I'm missing something but for now this is the way its happening
#
#Note: this does not save a newly created model in itself, which is good for when we need to check transition perms, etc
class GetOrGenerateObjectMixin(object):
    #TODO: This gets called on every get, do we need to generate the messages this early?
    def setup(self, request, *args, **kwargs):
        if kwargs.get('id'):
            self.object = get_object_or_404(self.model, id=kwargs.get('id'))
            self.msg = _("generic_objectUpdated_banner").format(object_type=self.object_friendly_name, object_id=self.object.id)
        elif not self.read_only:
            self.object = self.model()
            if(self.parent_model is not None):
                print("The object create method I didn't want called after create got called")
                setattr(self.object, self.parent_reference_name, get_object_or_404(self.parent_model, id=kwargs.get(self.parent_id_name)))
                if(self.parent_reference_name == "submission"):
                    setattr(self.object, "manuscript", self.object.submission.manuscript)
            self.msg = _("generic_objectCreated_banner").format(object_type=self.object_friendly_name)
        else:
            logger.error("Error with GetOrGenerateObjectMixin dispatch")
        return super(GetOrGenerateObjectMixin, self).setup(request, *args, **kwargs)
    
# class ChooseRoleFormMixin(object):
#     def dispatch(self, request, *args, **kwargs):
#         print("CHOOSE ROLE")
#         if(isinstance(self.object, m.Manuscript)):
#             self.form = self.form_dict[get_role_name_for_form(request.user, self.object, request.session)]
#         else:
#             self.form = self.form_dict[get_role_name_for_form(request.user, self.object.manuscript, request.session)]
#         return super(ChooseRoleFormMixin, self).dispatch(request,*args, **kwargs)

#A mixin that calls Django fsm has_transition_perm for an object
#It expects that the object has been grabbed already, for example by GetCreateObjectMixin    
#TODO: Is this specifically for noop transitions? if so we should name it that way.
class TransitionPermissionMixin(object):
    transition_on_parent = False
    def setup(self, request, *args, **kwargs):
        if(self.transition_on_parent):
            parent_object = getattr(self.object, self.parent_reference_name)
            transition_method = getattr(parent_object, self.transition_method_name)
        else:
            transition_method = getattr(self.object, self.transition_method_name)
        # logger.debug("User perms on object: " + str(get_perms(request.user, self.object))) #DEBUG
        # logger.debug(str(transition_method))
        if(not has_transition_perm(transition_method, request.user)):
            logger.debug("PermissionDenied")
            raise Http404()
        return super(TransitionPermissionMixin, self).setup(request, *args, **kwargs)    
    pass

#via https://gist.github.com/ceolson01/206139a093b3617155a6 , with edits
class GroupRequiredMixin(object):
    def setup(self, request, *args, **kwargs):
        if(len(self.groups_required)>0):
            if not request.user.is_authenticated:
                raise Http404()
            else:
                user_groups = []
                for group in request.user.groups.values_list('name', flat=True):
                    user_groups.append(group)
                if len(set(user_groups).intersection(self.groups_required)) <= 0:
                    raise Http404()
        return super(GroupRequiredMixin, self).setup(request, *args, **kwargs)

############################################# MANUSCRIPT #############################################

# Do not call directly
# We pass m_status here to provide the "progess" option. We want this to show up even if something is missing (e.g. no files) so that we can tell the user.
# ... but maybe this should be another case in the model
class GenericManuscriptView(GenericCorereObjectView):
    object_friendly_name = 'manuscript'
    model = m.Manuscript
    template = 'main/form_object_manuscript.html'
    author_formset = None
    data_source_formset = None
    keyword_formset = None 
    # v_metadata_formset = None
    role_name = None
    from_submission = False
    create = False
    form_helper = None
    dataverse_upload = False

    def dispatch(self, request, *args, **kwargs):
        if self.read_only:
            #All Manuscript fields are visible to all users, so no role-based forms
            self.form = f.ReadOnlyManuscriptForm
            if self.request.user.is_superuser or self.object.has_submissions():
                self.author_formset = f.ReadOnlyAuthorFormSet
                self.data_source_formset = f.ReadOnlyDataSourceFormSet
                self.keyword_formset = f.ReadOnlyKeywordFormSet
                # self.v_metadata_formset = f.ReadOnlyVMetadataManuscriptFormset
        else:
            self.role_name = get_role_name_for_form(request.user, self.object, request.session, self.create)
            if(self.dataverse_upload):
                self.form = f.ManuscriptFormDataverseUpload
            else:
                self.form = f.ManuscriptForms[self.role_name]
            if self.request.user.is_superuser or not self.create:
                self.author_formset = f.AuthorManuscriptFormsets[self.role_name]
                self.data_source_formset = f.DataSourceManuscriptFormsets[self.role_name]
                self.keyword_formset = f.KeywordManuscriptFormsets[self.role_name]
                # self.v_metadata_formset = f.VMetadataManuscriptFormsets[self.role_name]

        if(not self.object.has_submissions() and self.role_name == "Editor"): #we need a different form/helper for editor during create to hide certain fields
            self.form = f.ManuscriptForm_Editor_NoSubmissions
            self.form_helper = f.ManuscriptFormHelperEditor()
        if(self.dataverse_upload):
            self.form_helper = f.ManuscriptFormHelperDataverseUpload()
        else:
            self.form_helper = f.ManuscriptFormHelperMain()

        return super(GenericManuscriptView, self).dispatch(request,*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if(isinstance(self.object, m.Manuscript)):
            manuscript_display_name = self.object.get_display_name()
        else:
            manuscript_display_name = self.object.manuscript.get_display_name()

        #print(self.from_submission)
        if(self.from_submission):
            self.msg = _("manuscript_additionalInfoDuringSubmissionFlowHelpText_banner")
            messages.add_message(request, messages.INFO, self.msg)

        context = {'form': self.form, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'from_submission': self.from_submission,
            'm_status':self.object._status, 'page_title': self.page_title, 'page_help_text': self.page_help_text, 'role_name': self.role_name, 'helper': self.helper }#'

        if not self.create:
            context['manuscript_display_name'] = manuscript_display_name
        if self.request.user.is_superuser or not self.create:
            context['author_formset'] = self.author_formset(instance=self.object, prefix="author_formset")
            context['author_inline_helper'] = f.GenericInlineFormSetHelper(form_id='author')
            context['data_source_formset'] = self.data_source_formset(instance=self.object, prefix="data_source_formset")
            context['data_source_inline_helper'] = f.GenericInlineFormSetHelper(form_id='data_source')
            context['keyword_formset'] = self.keyword_formset(instance=self.object, prefix="keyword_formset")
            context['keyword_inline_helper'] = f.GenericInlineFormSetHelper(form_id='keyword')
            # context['v_metadata_formset'] = self.v_metadata_formset(instance=self.object, prefix="v_metadata_formset")

        if(self.from_submission):
            if(self.object.is_containerized()):
                progress_bar_html = generate_progress_bar_html(c.progress_list_container_submission, 'Update Manuscript')
            else:
                progress_bar_html = generate_progress_bar_html(c.progress_list_external_submission, 'Update Manuscript')
            context['progress_bar_html'] = progress_bar_html
        elif(self.create or self.object._status == m.Manuscript.Status.NEW):
            progress_bar_html = generate_progress_bar_html(c.progress_list_manuscript, 'Create Manuscript')
            context['progress_bar_html'] = progress_bar_html

        if(self.form_helper):
            context['manuscript_helper'] = self.form_helper
        #TODO: Add logic for manuscript creation

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        if self.request.user.is_superuser or not self.create:
            self.author_formset = self.author_formset(request.POST, instance=self.object, prefix="author_formset")
            self.data_source_formset = self.data_source_formset(request.POST, instance=self.object, prefix="data_source_formset")
            self.keyword_formset = self.keyword_formset(request.POST, instance=self.object, prefix="keyword_formset")
            # self.v_metadata_formset = self.v_metadata_formset(request.POST, instance=self.object, prefix="v_metadata_formset")

        if(isinstance(self.object, m.Manuscript)):
            manuscript_display_name = self.object.get_display_name()
        else:
            manuscript_display_name = self.object.manuscript.get_display_name()

        if not self.read_only and self.form.is_valid() \
            and (not self.author_formset or self.author_formset.is_valid()) and (not self.data_source_formset or self.data_source_formset.is_valid()) \
            and (not self.keyword_formset or self.keyword_formset.is_valid()):
            
            self.form.save()
            if(self.author_formset):
                self.author_formset.save()
            if(self.data_source_formset):
                self.data_source_formset.save()
            if(self.keyword_formset):
                self.keyword_formset.save()
            # if(self.v_metadata_formset):
            #     self.v_metadata_formset.save()

            if request.POST.get('submit_continue'):
                messages.add_message(request, messages.SUCCESS, self.msg)
                #return redirect('manuscript_addauthor', id=self.object.id)
                return redirect('manuscript_uploadfiles', id=self.object.id)

            if request.POST.get('submit_confirm'):
                messages.add_message(request, messages.SUCCESS, self.msg)
                #return redirect('manuscript_addauthor', id=self.object.id)
                return redirect('submission_confirmfilesbeforedataverseupload', id=self.object.get_latest_submission().id)

            #This logic needs a different way of detecting whether to go to the edit of a submission or creation
            #We should get the latest submission and check its status?
            elif request.POST.get('submit_continue_submission'):
                messages.add_message(request, messages.SUCCESS, self.msg)

                try: #If it already exists from the user going between the form pages
                    latest_sub = self.object.get_latest_submission()
                    if latest_sub._status == m.Submission.Status.RETURNED:
                        # return redirect('manuscript_createsubmission', manuscript_id=self.object.id)
                        submission = m.Submission.objects.create(manuscript=self.object)
                        print(submission)
                        return redirect('submission_uploadfiles', id=submission.id)
                    else:
                        return redirect('submission_uploadfiles', id=latest_sub.id)
                except m.Submission.DoesNotExist:
                    # return redirect('manuscript_createsubmission', manuscript_id=self.object.id)
                    submission = m.Submission.objects.create(manuscript=self.object)
                    return redirect('submission_uploadfiles', id=submission.id)
            else:
                return redirect(self.redirect)
        else:
            logger.debug(self.form.errors)      
            logger.debug(self.author_formset.errors)
            logger.debug(self.data_source_formset.errors)
            logger.debug(self.keyword_formset.errors)  
            # logger.debug(self.v_metadata_formset.errors)  

        context = {'form': self.form, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'from_submission': self.from_submission, 
            'm_status':self.object._status, 'page_title': self.page_title, 'page_help_text': self.page_help_text, 'role_name': self.role_name, 'helper': self.helper}

        if not self.create:
            context['manuscript_display_name'] = manuscript_display_name

        if self.request.user.is_superuser or not self.create:
            context['author_formset'] = self.author_formset
            context['author_inline_helper'] = f.GenericInlineFormSetHelper(form_id='author')
            context['data_source_formset'] = self.data_source_formset
            context['data_source_inline_helper'] = f.GenericInlineFormSetHelper(form_id='data_source')
            context['keyword_formset'] = self.keyword_formset
            context['keyword_inline_helper'] = f.GenericInlineFormSetHelper(form_id='keyword')
            # context['v_metadata_formset'] = self.v_metadata_formset

        if(self.from_submission):
            #We don't worry about compute_env = other here, as it won't normally be set. We default to showing "run code" even though it isn't certain.
            progress_bar_html = generate_progress_bar_html(c.progress_list_container_submission, 'Update Manuscript')
            context['progress_bar_html'] = progress_bar_html
        elif(self.create or self.object._status == m.Manuscript.Status.NEW):
            progress_bar_html = generate_progress_bar_html(c.progress_list_manuscript, 'Create Manuscript')
            context['progress_bar_html'] = progress_bar_html

        if(self.form_helper):
            context['manuscript_helper'] = self.form_helper

        return render(request, self.template, context)
           
#NOTE: LoginRequiredMixin has to be the leftmost. So we have to put it on every "real" view. Yes it sucks.
class ManuscriptCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, PermissionRequiredMixin, GenericManuscriptView):
    permission_required = c.perm_path(c.PERM_MANU_ADD_M)
    accept_global_perms = True
    return_403 = True
    page_title = _("manuscript_create_pageTitle")
    create = True
    redirect = "/"

class ManuscriptEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    #template = 'main/form_object_manuscript.html'
    transition_method_name = 'edit_noop'
    page_title = _("manuscript_edit_pageTitle")
    page_help_text = _("manuscript_edit_helpText")

class ManuscriptUpdateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    #template = 'main/form_object_manuscript.html'
    transition_method_name = 'edit_noop'
    page_title = _("manuscript_edit_pageTitle")
    from_submission = True
    page_help_text = _("manuscript_edit_helpText")

class ManuscriptReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericManuscriptView):
    #form_dict = f.ReadOnlyManuscriptForm #TODO: IMPLEMENT READONLY
    transition_method_name = 'view_noop'
    page_title = _("manuscript_view_pageTitle")
    http_method_names = ['get']
    read_only = True

#This is for the upload files page. The ajax uploader uses a different class
class ManuscriptUploadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericManuscriptView):
    form = f.ManuscriptFilesForm #TODO: Delete this if we really don't need a form?
    template = 'main/form_upload_files.html'
    transition_method_name = 'edit_files_noop'
    page_title = _("manuscript_uploadFiles_pageTitle")
                
    def dispatch(self, request, *args, **kwargs):
        if self.object._status == m.Manuscript.Status.NEW:
            self.page_help_text = _("manuscript_uploadFilesNew_helpText")
        return super(ManuscriptUploadFilesView, self).dispatch(request,*args, **kwargs)

    def get(self, request, *args, **kwargs):
        progress_bar_html = generate_progress_bar_html(c.progress_list_manuscript, 'Upload Files')

        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 'm_status':self.object._status, 
            'manuscript_display_name': self.object.get_display_name(), 'files_dict_list': list(self.files_dict_list), 'file_delete_url': self.file_delete_url, 'file_download_url': self.file_download_url, 
            'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master", 'page_title': self.page_title, 'page_help_text': self.page_help_text, 'progress_bar_html': progress_bar_html
            })

    def post(self, request, *args, **kwargs):
        if not self.read_only:
            errors = []
            changes_for_git = []
            try: 
                with transaction.atomic(): #to ensure we only save if there are no errors
                    for key, value in request.POST.items():
                        if(key.startswith("file:")):
                            skey = key.removeprefix("file:")
                            error_text = _helper_sanitary_file_check(value)
                            if(error_text):
                                raise ValueError(error_text)
                            if(skey != value):
                                before_path, before_name = skey.rsplit('/', 1) #need to catch if this fails, validation error
                                before_path = "/"+before_path
                                gfile = m.GitFile.objects.get(parent_manuscript=self.object, name=before_name, path=before_path)
                                after_path, after_name = value.rsplit('/', 1) #need to catch if this fails, validation error
                                after_path = "/" + after_path           
                                gfile.name=after_name
                                gfile.path=after_path
                                gfile.save()
                                changes_for_git.append({"old":skey, "new":value})
            except ValueError as e:
                errors.append(str(e))
                #TODO: As this code is used to catch more cases we'll need to differentiate when to log an error
                logger.error("User " + str(request.user.id) + " attempted to save a file with .. in the name. Seems fishy.")

            g.rename_manuscript_files(self.object, changes_for_git)

            if not errors and request.POST.get('submit_continue'):
                if list(self.files_dict_list):
                    return redirect('manuscript_addauthor', id=self.object.id)
                else:
                    errors.append(_('manuscript_noFiles_error'))
                
            progress_bar_html = generate_progress_bar_html(c.progress_list_manuscriptt, 'Upload Files')

            context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 'm_status':self.object._status, 'manuscript_display_name': self.object.get_display_name(), 
                'files_dict_list': list(self.object.get_gitfiles_pathname(combine=True)), 'file_delete_url': self.file_delete_url, 'file_download_url': self.file_download_url, 'progress_bar_html': progress_bar_html, 
                'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master", 'page_title': self.page_title, 'page_help_text': self.page_help_text
                }

            if(errors):
                print(errors)
                context['errors']= errors

            return render(request, self.template, context)

#Supports the ajax uploader performing file uploads
class ManuscriptUploaderView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    transition_method_name = 'edit_files_noop'
    http_method_names = ['post']

    #TODO: Should we making sure these files are safe?
    def post(self, request, *args, **kwargs):
        if not self.read_only:
            file = request.FILES.get('file')
            fullPath = request.POST.get('fullPath','')
            path = '/'+fullPath.rsplit(file.name)[0] #returns '' if fullPath is blank, e.g. file is on root

            if gitfiles := m.GitFile.objects.filter(parent_manuscript=self.object, path=path, name=file.name):
                g.delete_manuscript_file(self.object, fullRelPath+file.name)
                gitfiles[0].delete()    
                #return HttpResponse('File already exists', status=409)
            md5 = g.store_manuscript_file(self.object, file, path)
            #Create new GitFile for uploaded manuscript file
            git_file = m.GitFile()
            #git_file.git_hash = '' #we don't store this currently
            git_file.md5 = md5
            git_file.name = file.name
            git_file.path = path
            git_file.size = file.size
            git_file.parent_manuscript = self.object
            git_file.save(force_insert=True)

            #TODO: maybe centralize this flag setting to happen by the GitFile model
            self.object.files_changed = True
            self.object.save()
            
            return HttpResponse(status=200)

class ManuscriptDownloadFileView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    http_method_names = ['get']
    transition_method_name = 'view_noop'

    def get(self, request, *args, **kwargs):
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()

        return g.get_manuscript_file(self.object, file_path, True)

class ManuscriptDeleteFileView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    http_method_names = ['post']
    transition_method_name = 'edit_files_noop'

    def post(self, request, *args, **kwargs):
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        g.delete_manuscript_file(self.object, file_path)
        
        folder_path, file_name = file_path.rsplit('/',1)
        folder_path = folder_path + '/'
        try:
            m.GitFile.objects.get(parent_manuscript=self.object, path=folder_path, name=file_name).delete()
        except m.GitFile.DoesNotExist:
            logger.warning("While deleting file " + file_path + " on manuscript " + str(self.object.id) + ", the associated GitFile was not found. This could be due to a previous error during upload.")

        return HttpResponse(status=200)

#TODO: Pass less parameters, especially token stuff. Could combine with ManuscriptUploadFilesView, but how to handle parameters with that...
class ManuscriptReadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericManuscriptView):
    form = f.ManuscriptFilesForm #TODO: Delete this if we really don't need a form?
    template = 'main/form_upload_files.html'
    transition_method_name = 'view_noop'
    page_title = _("manuscript_viewFiles_pageTitle")
    http_method_names = ['get']
    read_only = True

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'manuscript_display_name': self.object.get_display_name(), 'files_dict_list': self.files_dict_list,
            'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":"master", 'page_title': self.page_title, 'page_help_text': self.page_help_text
            })

class ManuscriptFilesListAjaxView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericManuscriptView):
    template = 'main/file_list.html'
    transition_method_name = 'view_noop'

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 'page_title': self.page_title, 'page_help_text': self.page_help_text, 
            'file_delete_url': self.file_delete_url, 'file_download_url': self.file_download_url, 
            'manuscript_display_name': self.object.get_display_name(), 'files_dict_list': self.files_dict_list, 'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name})

# #NOTE: This is unused and disabled in URLs. Probably should delete.
# #Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
# #This and the other "progressviews" could be made generic, but I get the feeling we'll want to customize all the messaging and then it'll not really be worth it
# class ManuscriptProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericManuscriptView):
#     http_method_names = ['post']

#     def post(self, request, *args, **kwargs):
#         try:
#             if not fsm_check_transition_perm(self.object.begin, request.user): 
#                 print(str(self.object))
#                 logger.error("PermissionDenied")
#                 raise Http404()
#             try:
#                 self.object.begin()
#                 self.object.save()
#             except TransitionNotAllowed as e:
#                 logger.error("TransitionNotAllowed: " + str(e))
#                 raise

#         except (TransitionNotAllowed):
#             ### Messaging ###
#             self.msg = _("manuscript_objectTransferAuthorFailure_banner_forEditor").format(object_id=self.object_id, object_title=self.object.get_display_name())
#             messages.add_message(request, messages.ERROR, self.msg)
#             ### End Messaging ###
#         return redirect('/manuscript/'+str(self.object.id))


#TODO: Delete this and manuscript_report.html. Holding onto these for a bit incase we need to use them to display the content not as a pdf (though the style is stale)
# class ManuscriptReportView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericManuscriptView):
#     template = 'main/manuscript_report.html'

#     def get(self, request, *args, **kwargs):
#         return render(request, self.template, {'manuscript': self.object})



#This is a somewhat working example with the renderpdf library. But I think maybe using django-weasyprint is a better choice
#PDFView acts like a TemplateView
#Note that under the hood this uses https://doc.courtbouillon.org/weasyprint/stable/
class ManuscriptReportDownloadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, PDFView):
    template_name = 'main/manuscript_report_download.html'
    prompt_download = True
    transition_method_name = 'view_noop'
    model = m.Manuscript
    object_friendly_name = 'manuscript'
    download_name = "verification_report.pdf"

    def get_context_data(self, *args, **kwargs):
        """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        context['manuscript'] = self.object #get_object_or_404(m.Manuscript, id=kwargs.get('id'))

        return context

class ManuscriptDownloadAllFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    http_method_names = ['get']
    transition_method_name = 'view_noop'
    model = m.Manuscript
    object_friendly_name = 'manuscript'

    def get(self, request, *args, **kwargs):
        return g.download_all_manuscript_files(self.object)

class ManuscriptEditConfirmBeforeDataverseUploadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    http_method_names = ['get','post']
    transition_method_name = 'dataverse_upload_noop' #TODO: is it ok to call as non noop transition here? If so, remove comment in TransitionPermissionMixin
    model = m.Manuscript
    object_friendly_name = 'manuscript'
    page_title = "Upload To Dataverse" #_("manuscript_edit_pageTitle")
    page_help_text = "Please confirm the information in these fields before they are pushed to Dataverse" #_("manuscript_edit_helpText")
    dataverse_upload = True

class ManuscriptPullCitationFromDataverseView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericManuscriptView):
    http_method_names = ['get']
    transition_method_name = 'dataverse_pull_citation_noop' #TODO: is it ok to call as non noop transition here? If so, remove comment in TransitionPermissionMixin
    model = m.Manuscript
    object_friendly_name = 'manuscript'

    def get(self, request, *args, **kwargs):
        try:
            dv.update_citation_data(self.object)
            self.msg= 'Information from dataset ' + self.object.dataverse_fetched_doi + ' has been fetched. Information can be confirmed by viewing the <a href="./reportdownload">verification report</a>.'
            messages.add_message(request, messages.SUCCESS, mark_safe(self.msg))

        except Exception as e: #for now we catch all exceptions and present them as a message
            self.msg= 'An error has occurred attempting to pull citation data from Dataverse: ' + str(e)
            messages.add_message(request, messages.ERROR, self.msg)

        return redirect('manuscript_landing', id=self.object.id)

############################################# SUBMISSION #############################################

#See commit f9f9a1f205c21f6e883bb91f767a57ba69879a35 or older for old saving code for v_metadata audit / badge / etc. We probably need this again for our "push to dataverse" step

# Do not call directly. Used for the main submission form
class GenericSubmissionFormView(GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    note_formset = f.NoteSubmissionFormset
    note_helper = f.NoteFormSetHelper()
    prev_sub_vmetadata = None

    edition_formset = None
    curation_formset = None
    verification_formset = None
    submission_editor_date_formset = None

    def dispatch(self, request, *args, **kwargs):
        role_name = get_role_name_for_form(request.user, self.object.manuscript, request.session, False)
        try:
            if(not self.read_only and (has_transition_perm(self.object.manuscript.add_submission_noop, request.user) or has_transition_perm(self.object.edit_noop, request.user))):
                self.form = f.SubmissionForms[role_name]
            elif(has_transition_perm(self.object.view_noop, request.user)):
                self.form = f.ReadOnlySubmissionForm
        except (m.Submission.DoesNotExist, KeyError):
            pass
        try:
            if(not self.read_only and (has_transition_perm(self.object.add_edition_noop, request.user) or has_transition_perm(self.object.submission_edition.edit_noop, request.user))):
                self.edition_formset = f.EditionSubmissionFormsets[role_name]
                self.page_title = _("submission_review_helpText").format(submission_version=self.object.version_id) 
                self.page_help_text = _("submission_editionReview_helpText")
            elif(has_transition_perm(self.object.submission_edition.view_noop, request.user)):
                self.edition_formset = f.ReadOnlyEditionSubmissionFormset
        except (m.Edition.DoesNotExist, KeyError):
            pass
        try:
            if(not self.read_only and (has_transition_perm(self.object.add_curation_noop, request.user) or has_transition_perm(self.object.submission_curation.edit_noop, request.user))):
                if self.object._status !=  m.Submission.Status.IN_PROGRESS_CURATION: #We show our later edit form with only certain fields editable
                    self.curation_formset = f.EditOutOfPhaseCurationFormset
                else:
                    self.curation_formset = f.CurationSubmissionFormsets[role_name]
                self.page_title = _("submission_review_helpText").format(submission_version=self.object.version_id) 
                self.page_help_text = _("submission_curationReview_helpText")

                if self.object.manuscript.skip_edition:
                    self.submission_editor_date_formset = f.SubmissionEditorDateFormset
            elif(has_transition_perm(self.object.submission_curation.view_noop, request.user)):
                self.curation_formset = f.ReadOnlyCurationSubmissionFormset
                #We may need a read_only SubmissionEditorDateFormset for here

        except (m.Curation.DoesNotExist, KeyError):
            pass
        try:
            if(not self.read_only and (has_transition_perm(self.object.add_verification_noop, request.user) or has_transition_perm(self.object.submission_verification.edit_noop, request.user))):
                if self.object._status !=  m.Submission.Status.IN_PROGRESS_VERIFICATION: #We show our later edit form with only certain fields editable
                    self.verification_formset = f.EditOutOfPhaseVerificationFormset
                else:
                    self.verification_formset = f.VerificationSubmissionFormsets[role_name]
                self.page_title = _("submission_review_helpText").format(submission_version=self.object.version_id) 
                self.page_help_text = _("submission_verificationReview_helpText")
            elif(has_transition_perm(self.object.submission_verification.view_noop, request.user)):
                self.verification_formset = f.ReadOnlyVerificationSubmissionFormset
        except (m.Verification.DoesNotExist, KeyError):
            pass

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        manuscript_display_name = self.object.manuscript.get_display_name()
        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'inline_helper': f.GenericInlineFormSetHelper(), 's_version': self.object.version_id,
            'page_title': self.page_title, 'page_help_text': self.page_help_text, 'manuscript_display_name': manuscript_display_name, 's_status':self.object._status, 'parent_id': self.object.manuscript.id}

        if not self.read_only:
            context['progress_bar_html'] = get_progress_bar_html_submission('Add Submission Info', self.object)

        context['is_manu_curator'] = request.user.groups.filter(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.object.manuscript.id)).exists() or request.user.is_superuser #Used to enable delete option for all notes in JS

        if(self.note_formset is not None):
            checkers = [ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_AUTHOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_EDITOR)),
                ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_CURATOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_VERIFIER))]
            notes = m.Note.objects.filter(parent_submission=self.object)
            for checker in checkers:
                checker.prefetch_perms(notes)
            sub_files = self.object.submission_files.all().order_by('path','name')

            context['note_formset'] = self.note_formset(instance=self.object, prefix="note_formset", 
                form_kwargs={'checkers': checkers, 'manuscript': self.object.manuscript, 'submission': self.object, 'sub_files': sub_files}) #TODO: This was set to `= formset`, maybe can delete that variable now?
        
        if(self.edition_formset is not None):
            context['edition_formset'] = self.edition_formset(instance=self.object, prefix="edition_formset")
        if(self.curation_formset is not None):
            context['curation_formset'] = self.curation_formset(instance=self.object, prefix="curation_formset")
        if(self.verification_formset is not None):
            context['verification_formset'] = self.verification_formset(instance=self.object, prefix="verification_formset")
        if(self.submission_editor_date_formset is not None):
            context['submission_editor_date_formset'] = self.submission_editor_date_formset(queryset=m.Submission.objects.filter(id=self.object.id), prefix="submission_editor_date_formset")

        if(self.note_helper is not None):
            context['note_helper'] = self.note_helper

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        self.redirect = "/manuscript/"+str(self.object.manuscript.id)

        manuscript_display_name = self.object.manuscript.get_display_name()

        if(self.note_formset):
            checkers = [ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_AUTHOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_EDITOR)),
                ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_CURATOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_VERIFIER))]
            notes = m.Note.objects.filter(parent_submission=self.object)
            for checker in checkers:
                checker.prefetch_perms(notes)
            sub_files = self.object.submission_files.all().order_by('path','name')

            self.note_formset = self.note_formset(request.POST, instance=self.object, prefix="note_formset", 
                form_kwargs={'checkers': checkers, 'manuscript': self.object.manuscript, 'submission': self.object, 'sub_files': sub_files}) #TODO: This was set to `= formset`, maybe can delete that variable now?
        if(self.edition_formset):
            self.edition_formset = self.edition_formset(request.POST, instance=self.object, prefix="edition_formset")
        if(self.curation_formset):
            self.curation_formset = self.curation_formset(request.POST, instance=self.object, prefix="curation_formset")
        if(self.submission_editor_date_formset):
            print("POST LOAD EDITOR DATE")
            self.submission_editor_date_formset = self.submission_editor_date_formset(request.POST, queryset=m.Submission.objects.filter(id=self.object.id), prefix="submission_editor_date_formset")
        if(self.verification_formset):
            self.verification_formset = self.verification_formset(request.POST, instance=self.object, prefix="verification_formset")

        #This code checks whether to attempt saving, seeing that each formset that exists is valid
        #If we have to add even more formsets, we should consider creating a list of formsets to check dynamically
        if not self.read_only:
            if self.note_formset is not None:
                if self.note_formset.is_valid():
                    self.note_formset.save()
                else:
                    for fr in self.note_formset.forms:
                        if(fr.is_valid()):
                            fr.save(True)

            #This code handles the case where a curator-admin needs to edit their curation while a verification is available. If they don't change the verification, they can still save the curation.
            hide_v_errors = False
            if not self.read_only and (has_transition_perm(self.object.add_curation_noop, request.user) or has_transition_perm(self.object.submission_curation.edit_noop, request.user)):
                if self.verification_formset and self.verification_formset[0].changed_data == []:
                    if not request.POST.get('submit_progress_verification'):
                        hide_v_errors = True

            #NOTE: The user.is_superuser and extra verification formset valid checks are in here to handle editing out of phase by curator-admins.
            #      Curator-admins need to be able to edit their curation while a verification is happening, and without this verification validation will stop saving.
            #      This fix just hides the validation errors, a better one may be needed. Maybe something that allows partial saves if not submitting.        
            if( self.form.is_valid() and (self.edition_formset is None or self.edition_formset.is_valid()) and (self.curation_formset is None or self.curation_formset.is_valid()) 
                and (self.verification_formset is None or self.verification_formset.is_valid() or hide_v_errors) #and (self.v_metadata_formset is None or self.v_metadata_formset.is_valid()) 
                ):
                self.form.save()

                if(self.submission_editor_date_formset):
                    o_id = self.object.id
                    self.submission_editor_date_formset.save()
                    self.object = self.model.objects.get(id=o_id) #We re-fetch the object here to ensure that the saves below don't wipe out the date. Not quite sure why this is needed
                if(self.edition_formset):
                    self.edition_formset.save()
                if(self.curation_formset):
                    self.curation_formset.save()
                if(self.verification_formset and self.verification_formset.is_valid()):
                    self.verification_formset.save()

                try:
                    status = None
                    if request.POST.get('submit_progress_edition'):
                        if not fsm_check_transition_perm(self.object.submit_edition, request.user):
                            logger.debug("PermissionDenied")
                            raise Http404()
                        status = self.object.submit_edition()
                        self.object.save()                
                    elif request.POST.get('submit_progress_curation'):
                        if not fsm_check_transition_perm(self.object.review_curation, request.user):
                            logger.debug("PermissionDenied")
                            raise Http404()
                        status = self.object.review_curation()
                        self.object.save()
                    elif request.POST.get('submit_progress_verification'):
                        if self.verification_formset and self.verification_formset.is_valid():
                            if not fsm_check_transition_perm(self.object.review_verification, request.user):
                                logger.debug("PermissionDenied")
                                raise Http404()
                            status = self.object.review_verification()
                            self.object.save()
                        
                    if ((self.object.manuscript.skip_edition and request.POST.get('submit_progress_curation'))
                        or (not self.object.manuscript.skip_edition and request.POST.get('submit_progress_edition'))):
                        if self.object.manuscript.is_containerized() and settings.CONTAINER_DRIVER == 'wholetale':
                            #Here we create the wholetale version. 
                            # If not skipping editor, we do this after the editors approval because it isn't really a "done" submission then
                            # Else, we do it after curator approval because that's the next step.
                            wtc = w.WholeTaleCorere(admin=True)
                            tale_original = self.object.submission_tales.get(original_tale=None)    
                            result = wtc.create_tale_version(tale_original.wt_id, w.get_tale_version_name(self.object.version_id))
                    ### Messaging ###
                    if(status != None):
                        if(status == m.Submission.Status.IN_PROGRESS_CURATION):
                            #Send message/notification to curators that the submission is ready
                            recipients = m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.object.manuscript.id)) 
                            notification_msg = _("submission_objectTransfer_notification_forEditorCuratorVerifier").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
                            notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
                            for u in recipients: #We have to loop to get the user model fields
                                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
                        elif(status == m.Submission.Status.IN_PROGRESS_VERIFICATION):
                            #Send message/notification to verifiers that the submission is ready
                            recipients = m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.object.manuscript.id)) 
                            notification_msg = _("submission_objectTransfer_notification_forEditorCuratorVerifier").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
                            notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
                            for u in recipients: #We have to loop to get the user model fields
                                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
                        elif(status == m.Submission.Status.REVIEWED_AWAITING_REPORT):
                            #Send message/notification to curators that the submission is ready for its report to be returned, This can happen when a verifier finishes verifying, or a curator finishes curating and skips verification
                            recipients = m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.object.manuscript.id)) 
                            notification_msg = _("submission_objectReviewed_notification_forCurator").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
                            notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
                            for u in recipients: #We have to loop to get the user model fields
                                send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
                    ### End Messaging ###

                except TransitionNotAllowed as e:
                    logger.error("TransitionNotAllowed: " + str(e))
                    raise

                if request.POST.get('back_save'):
                    return redirect('submission_notebook', id=self.object.id)

                if request.POST.get('submit_continue'):
                    messages.add_message(request, messages.SUCCESS, self.msg)
                    return _helper_submit_submission_and_redirect(request, self.object)

                return redirect(self.redirect)

            else:
                if(self.edition_formset):
                    logger.debug(self.edition_formset.errors)
                if(self.curation_formset):
                    logger.debug(self.curation_formset.errors)
                if(self.submission_editor_date_formset):
                    logger.debug(self.submission_editor_date_formset.errors)
                if(self.verification_formset):
                    logger.debug(self.verification_formset.errors)

        else: #readonly
            if self.note_formset is not None:
                if self.note_formset.is_valid():
                    self.note_formset.save()
                else:
                    for fr in self.note_formset.forms:
                        if(fr.is_valid()):
                            fr.save(True)
                return redirect(self.redirect) #This redirect was added mostly because the latest note was getting hidden after save. I'm not sure why that formset doesn't get updated with a new blank.

        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create, 'inline_helper': f.GenericInlineFormSetHelper(), 's_version': self.object.version_id,
            'page_title': self.page_title, 'page_help_text': self.page_help_text, 'manuscript_display_name': manuscript_display_name, 's_status':self.object._status, 'parent_id': self.object.manuscript.id}
        
        if not self.read_only: #should never hit post if read_only but yea
            context['progress_bar_html'] = get_progress_bar_html_submission('Add Submission Info', self.object)
        
        context['is_manu_curator'] = request.user.groups.filter(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.object.manuscript.id)).exists() or request.user.is_superuser #Used to enable delete option for all notes in JS

        if(self.note_formset is not None):
            #We re-init the note formset to not show the validation errors. There may be an easier and more efficient way
            checkers = [ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_AUTHOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_EDITOR)),
                ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_CURATOR)), ObjectPermissionChecker(Group.objects.get(name=c.GROUP_ROLE_VERIFIER))]
            notes = m.Note.objects.filter(parent_submission=self.object)
            for checker in checkers:
                checker.prefetch_perms(notes)
            sub_files = self.object.submission_files.all().order_by('path','name')

            context['note_formset'] = f.NoteSubmissionFormset(instance=self.object, prefix="note_formset", 
                form_kwargs={'checkers': checkers, 'manuscript': self.object.manuscript, 'submission': self.object, 'sub_files': sub_files})

        if(self.edition_formset is not None):
            context['edition_formset'] = self.edition_formset
        if(self.curation_formset is not None):
            context['curation_formset'] = self.curation_formset
        if(self.verification_formset is not None):
            context['verification_formset'] = self.verification_formset
        if(self.submission_editor_date_formset is not None):
            context['submission_editor_date_formset'] = self.submission_editor_date_formset

        if(self.note_helper is not None):
            context['note_helper'] = self.note_helper

        return render(request, self.template, context)

class SubmissionCreateView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericSubmissionFormView):
    transition_method_name = 'add_submission_noop'
    transition_on_parent = True
    page_title = _("submission_create_pageTitle")
    page_help_text = _("submission_info_helpText")
    template = 'main/form_object_submission.html'
    create = True

    # def get(self, request, *args, **kwargs):
    #     return super(SubmissionCreateView, self).get(request,*args, **kwargs)

#Removed TransitionPermissionMixin because multiple cases can edit. We do all the checking inside the view
#TODO: Should we combine this view with the read view? There will be cases where you can edit a review but not the main form maybe?
class SubmissionEditView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericSubmissionFormView):
    transition_method_name = 'edit_noop'
    page_help_text = _("submission_info_helpText") #Sometimes overwritten by GenericSubmissionFormView
    template = 'main/form_object_submission.html'

    def dispatch(self, request, *args, **kwargs):
        self.page_title = _("submission_info_pageTitle").format(submission_version=self.object.version_id) #Sometimes overwritten by GenericSubmissionFormView
        return super().dispatch(request, *args, **kwargs)

class SubmissionReadView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericSubmissionFormView):
    form = f.ReadOnlySubmissionForm
    transition_method_name = 'view_noop'
    read_only = True #We still allow post because you can still create/edit notes.
    template = 'main/form_object_submission.html'

    def dispatch(self, request, *args, **kwargs):
        self.page_title = _("submission_view_pageTitle").format(submission_version=self.object.version_id)
        return super().dispatch(request, *args, **kwargs)


##### THESE FILE METADATA COLLECTING CLASSES ARE DISABLED FOR NOW. WE MAY WANT THEM EVENTUALLY TO COLLECT DESCRIPTION/TAGS FOR DATAVERSE ###

# TODO: Do we need all the parameters being passed? Especially for read?
# TODO: I'm a bit surprised this doesn't blow up when posting with invalid data. The root post is used (I think). Maybe the get is called after to render the page?
# class GenericSubmissionFilesMetadataView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericCorereObjectView):
#     template = 'main/form_edit_files.html'
#     helper=f.GitFileFormSetHelper()
#     parent_reference_name = 'manuscript'
#     parent_id_name = "manuscript_id"
#     parent_model = m.Manuscript
#     object_friendly_name = 'submission'
#     model = m.Submission

#     def get(self, request, *args, **kwargs):
#         #TODO: Can we just refer to form for everything and delete a bunch of stuff?
#         formset = self.form

#         context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
#             'manuscript_display_name': self.object.manuscript.get_display_name(), 'files_dict_list': self.files_dict_list, 's_status':self.object._status, 'parent_id': self.object.manuscript.id,
#             'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":g.helper_get_submission_branch_name(self.object),
#             'children_formset':formset, 'page_title': self.page_title, 'page_help_text': self.page_help_text}

#         if(self.object._status == m.Submission.Status.NEW or self.object._status == m.Submission.Status.REJECTED_EDITOR):
#             if(self.object.manuscript._status == m.Manuscript.Status.AWAITING_INITIAL):
#                 progress_list = c.progress_list_container_submission_first
#             else:
#                 progress_list = c.progress_list_container_submission_subsequent
#             progress_bar_html = generate_progress_bar_html(progress_list, 'Add File Metadata')
#             context['progress_bar_html'] = progress_bar_html

#         return render(request, self.template, context)

#     #Originally copied from GenericCorereObjectView
#     def post(self, request, *args, **kwargs):
#         formset = self.form
#         if formset.is_valid():
#             if not self.read_only:
#                 formset.save() #Note: this is what saves a newly created model instance
#                 if request.POST.get('back_save'):
#                     if (settings.SKIP_DOCKER):
#                         self.msg = "SKIP_DOCKER enabled in settings. Docker container step has been bypassed."
#                         messages.add_message(request, messages.INFO, self.msg)
#                         return redirect('submission_uploadfiles', id=self.object.id)
#                     container_flow_address = _helper_get_oauth_url(request, self.object)
#                     return redirect(container_flow_address)
#                 #NOTE: This logic has been extracted into a helper method in this file
#                 elif self.object._status == self.object.Status.NEW or self.object._status == self.object.Status.REJECTED_EDITOR:
#                     if not fsm_check_transition_perm(self.object.submit, request.user): 
#                         logger.debug("PermissionDenied")
#                         raise Http404()
#                     self.object.submit(request.user)
#                     self.object.save()

#                     ## Messaging ###
#                     self.msg= _("submission_objectTransferEditorBeginSuccess_banner_forAuthor").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
#                     messages.add_message(request, messages.SUCCESS, self.msg)
#                     logger.info(self.msg)
#                     recipients = m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.object.manuscript.id)) 
#                     notification_msg = _("submission_objectTransfer_notification_forEditorCuratorVerifier").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
#                     notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
#                     for u in recipients: #We have to loop to get the user model fields
#                         send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
#                     ## End Messaging ###

#                     # self.msg = _("submission_submitted_banner")
#                     # messages.add_message(request, messages.SUCCESS, self.msg)
#                     return redirect('manuscript_landing', id=self.object.manuscript.id)
#                 else:
#                     messages.add_message(request, messages.SUCCESS, self.msg)
#                     return redirect('manuscript_landing', id=self.object.manuscript.id)
#         else:
#             logger.debug(formset.errors)

#         context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
#             'manuscript_display_name': self.object.manuscript.get_display_name(), 'files_dict_list': self.files_dict_list, 's_status':self.object._status, 'parent_id': self.object.manuscript.id,
#             'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, "repo_branch":g.helper_get_submission_branch_name(self.object),
#             'parent':self.object, 'children_formset':formset, 'page_title': self.page_title, 'page_help_text': self.page_help_text}

#         if(self.object._status == m.Submission.Status.NEW or self.object._status == m.Submission.Status.REJECTED_EDITOR):
#             if(self.object.manuscript._status == m.Manuscript.Status.AWAITING_INITIAL):
#                 progress_list = c.progress_list_container_submission_first
#             else:
#                 progress_list = c.progress_list_container_submission_subsequent
#             progress_bar_html = generate_progress_bar_html(progress_list, 'Add File Metadata')
#             context['progress_bar_html'] = progress_bar_html

#         return render(request, self.template, context)

# class SubmissionEditFilesView(GenericSubmissionFilesMetadataView):
#     transition_method_name = 'edit_noop'
#     page_help_text = _("submission_editFilesMetadata_helpText")
#     form = f.GitFileFormSet

#     def dispatch(self, request, *args, **kwargs):
#         self.page_title = _("submission_editFilesMetadata_pageTitle").format(submission_version=self.object.version_id)
#         return super().dispatch(request, *args, **kwargs)

# class SubmissionReadFilesView(GenericSubmissionFilesMetadataView):
#     transition_method_name = 'view_noop'
#     form = f.GitFileReadOnlyFileFormSet
#     read_only = True

#     def dispatch(self, request, *args, **kwargs):
#         self.page_title = _("submission_viewFileMetadata_pageTitle").format(submission_version=self.object.version_id)
#         return super().dispatch(request, *args, **kwargs)

#NOTE: The template connected to this does not use dataverse_upload currently, could be removed
#This is for the upload files page. The ajax uploader uses a different class
class SubmissionUploadFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericCorereObjectView):
    #TODO: Maybe don't need some of these, after creating uploader
    form = f.SubmissionUploadFilesForm
    template = 'main/form_upload_files.html'
    transition_method_name = 'edit_noop'
    page_help_text = _("submission_uploadFiles_helpText")
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    dataverse_upload = False

    def dispatch(self, request, *args, **kwargs):
        if self.read_only:
            self.page_title = _("submission_viewFiles_pageTitle").format(submission_version=self.object.version_id)
        elif self.dataverse_upload:
            self.page_title = _("submission_completeFiles_pageTitle").format()
            self.page_help_text = _("submission_completeFiles_helpText").format(dataverse=self.object.manuscript.dataverse_parent,installation=self.object.manuscript.dataverse_installation.name)
        else:
            self.page_title = _("submission_uploadFiles_pageTitle").format(submission_version=self.object.version_id)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 
            'manuscript_display_name': self.object.manuscript.get_display_name(), 'files_dict_list': list(self.files_dict_list), 's_status':self.object._status,
            'file_delete_url': self.file_delete_url, 'file_download_url': self.file_download_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, 
            "repo_branch":g.helper_get_submission_branch_name(self.object), 'page_title': self.page_title, 'page_help_text': self.page_help_text, 'dataverse_upload': self.dataverse_upload,
            'skip_docker': settings.SKIP_DOCKER, 'containerized': self.object.manuscript.is_containerized(), 'manuscript_id': self.object.manuscript.id}
        
        if self.dataverse_upload:
            context['dataverse_upload'] = self.dataverse_upload

        if not self.read_only and not self.dataverse_upload:
            context['progress_bar_html'] = get_progress_bar_html_submission('Upload Files', self.object)

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        if not self.read_only:
            self.object.save() #This saves our new submission, now that we've moved our old create pageSubmissionCreateView #The comment/code before this may be unneeded now that we always do manuscript edit first

            errors = []

            ## TODO: Use this code and then remove after implementing ajax based datatable file renaming

            # changes_for_git = []
            #
            # try: #File Renaming
            #     with transaction.atomic(): #to ensure we only save if there are no errors
            #         for key, value in request.POST.items():
            #             if(key.startswith("file:")):
            #                 skey = key.removeprefix("file:")
            #                 if(skey != value):
            #                     error_text = _helper_sanitary_file_check(value)
            #                     if(error_text):
            #                         raise ValueError(error_text)
            #                     before_path, before_name = skey.rsplit('/', 1) #need to catch if this fails, validation error
            #                     before_path = "/"+before_path
            #                     gfile = m.GitFile.objects.get(parent_submission=self.object, name=before_name, path=before_path)
            #                     after_path, after_name = value.rsplit('/', 1) #need to catch if this fails, validation error
            #                     after_path = "/" + after_path                      
            #                     gfile.name=after_name
            #                     gfile.path=after_path
            #                     gfile.save()
            #                     changes_for_git.append({"old":skey, "new":value})
            #                     self.object.files_changed = True
            #                     self.object.save()
            # except ValueError as e:
            #     errors.append(str(e))
            #     #TODO: As this code is used to catch more cases we'll need to differentiate when to log an error
            #     logger.error("User " + str(request.user.id) + " attempted to save a file with .. in the name. Seems fishy.")

            # g.rename_submission_files(self.object.manuscript, changes_for_git)

            if not errors and request.POST.get('submit_dataverse_upload'):
                old_doi = self.object.manuscript.dataverse_fetched_doi
                #TODO: This url will be bad if the dataverse_uploader changes the dataverse targeted, because the change will have happened in the previous form.
                old_dv_url = self.object.manuscript.dataverse_installation.url
                try:
                    dv.upload_manuscript_data_to_dataverse(self.object.manuscript)
                    if old_doi and old_doi != self.object.manuscript.dataverse_fetched_doi: #I don't actually know why I'm checking doi equality here... we could probably just check old_doi existing
                        self.msg = 'You have uploaded the manuscript, which created a new dataset. You may want to go to <a href="' + old_dv_url + '/dataset.xhtml?persistentId=' + old_doi + '">' + old_doi + '</a> and delete the previous dataset.'
                        messages.add_message(request, messages.SUCCESS, mark_safe(self.msg))
                    else: 
                        self.msg = 'You have uploaded the manuscript data to Dataverse, creating a new dataset.'
                        messages.add_message(request, messages.SUCCESS, mark_safe(self.msg))
                    return redirect('manuscript_landing', id=self.object.manuscript.id)

                except Exception as e: #for now we catch all exceptions and present them as a message
                    self.msg= 'An error has occurred attempting to upload to Dataverse: ' + str(e)
                    messages.add_message(request, messages.ERROR, self.msg)

            if not errors and request.POST.get('submit_continue'):
                if list(self.files_dict_list):
                    if settings.SKIP_DOCKER or not self.object.manuscript.is_containerized():
                        return redirect('submission_info', id=self.object.id)
                    elif settings.CONTAINER_DRIVER == 'wholetale':
                        if self.object.files_changed:
                            wtc = w.WholeTaleCorere(request.COOKIES.get('girderToken'))
                            tale = self.object.submission_tales.get(original_tale=None) #we always upload to the original tale
                            wtc.delete_tale_files(tale.wt_id)
                            wtc.upload_files(tale.wt_id, g.get_submission_files_path(self.object.manuscript))
                            wtc_instance = wtc.create_instance_with_purge(tale, request.user) #this may take a long time      
                            try: #If instance model object already exists, delete it
                                wtm.Instance.objects.get(tale=tale, corere_user=request.user).delete()
                            except wtm.Instance.DoesNotExist:
                                pass
                            wtm.Instance.objects.create(tale=tale, wt_id=wtc_instance['_id'], corere_user=request.user)
                            self.object.files_changed = False
                            self.object.save()

                        return redirect('submission_notebook', id=self.object.id)

                    else:
                        if(hasattr(self.object.manuscript, 'manuscript_localcontainerinfo')):
                            if self.object.manuscript.manuscript_localcontainerinfo.build_in_progress:
                                while self.object.manuscript.manuscript_localcontainerinfo.build_in_progress:
                                    time.sleep(.1)
                                    self.object.manuscript.manuscript_localcontainerinfo.refresh_from_db()
                            
                            elif(self.object.files_changed):
                                logger.info("Refreshing docker stack for manuscript: " + str(self.object.manuscript.id))
                                d.refresh_notebook_stack(self.object.manuscript)
                                self.object.files_changed = False
                                self.object.save()
                        else:
                            logger.info("Building docker stack for manuscript: " + str(self.object.manuscript.id))
                            d.build_manuscript_docker_stack(self.object.manuscript, request)
                            self.object.files_changed = False
                            self.object.save()

                        container_flow_address = _helper_get_oauth_url(request, self.object)

                        #Note: We redirect to the oauth page not in an iframe. When that it done it redirects back to our UIs iframe.
                        return redirect(container_flow_address)

                errors.append(_('submission_noFiles_error'))
            
            context = {'form': self.form, 'helper': self.helper, 'read_only': self.read_only, 'manuscript_id': self.object.manuscript.id,
                'manuscript_display_name': self.object.manuscript.get_display_name(), 'files_dict_list': list(self.object.get_gitfiles_pathname(combine=True)), 's_status':self.object._status,
                'file_delete_url': self.file_delete_url, 'file_download_url': self.file_download_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, 'dataverse_upload': self.dataverse_upload,
                "repo_branch":g.helper_get_submission_branch_name(self.object), 'page_title': self.page_title, 'page_help_text': self.page_help_text, 'skip_docker': settings.SKIP_DOCKER, 'containerized': self.object.manuscript.is_containerized(),}

            if self.dataverse_upload:
                context['dataverse_upload'] = self.dataverse_upload

            if not self.read_only and not self.dataverse_upload: #should never hit post if read_only but yea
                context['progress_bar_html'] = get_progress_bar_html_submission('Upload Files', self.object)

            if(errors):
                context['errors']= errors

            return render(request, self.template, context)


class SubmissionReadFilesView(SubmissionUploadFilesView):
    transition_method_name = 'view_noop'
    form = f.GitFileReadOnlyFileFormSet
    read_only = True

    # def dispatch(self, request, *args, **kwargs):
    #     #TODO: I'm not sure if this title actually does anything
    #     self.page_title = _("submission_viewFiles_pageTitle").format(submission_version=self.object.version_id)
    #     return super().dispatch(request, *args, **kwargs)

#TODO: This needs to pass m_status but isn't
class SubmissionCompleteFilesBeforeDataverseUploadView(SubmissionUploadFilesView):
    transition_on_parent = True
    transition_method_name = 'dataverse_upload_noop'
    #page_help_text = _("submission_completeFiles_helpText") #set in SubmissionUploadFilesView, as we pass arguments to it
    dataverse_upload = True #tell parent view to pass m_status even though is a sub
    pass

#Supports the ajax uploader performing file uploads
class SubmissionUploaderView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericCorereObjectView):
    #TODO: Probably don't need some of these, after creating uploader
    transition_method_name = 'edit_noop'
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    model = m.Submission
    object_friendly_name = 'submission'
    http_method_names = ['post']

    #TODO: Should we making sure these files are safe?
    def post(self, request, *args, **kwargs):
        if not self.read_only:
            file = request.FILES.get('file')
            fullRelPath = request.POST.get('fullPath','')
            print(file)
            print(fullRelPath)
            path = '/'+fullRelPath.rsplit(file.name)[0] #returns '' if fullPath is blank, e.g. file is on root
            print(path)
            if gitfiles := m.GitFile.objects.filter(parent_submission=self.object, path=path, name=file.name):
                g.delete_submission_file(self.object.manuscript, fullRelPath+file.name)
                gitfiles[0].delete()    
                #return HttpResponse('File already exists', status=409)
            md5 = g.store_submission_file(self.object.manuscript, file, path)
            #Create new GitFile for uploaded submission file
            git_file = m.GitFile()
            #git_file.git_hash = '' #we don't store this currently
            git_file.md5 = md5
            git_file.name = file.name
            git_file.path = path
            git_file.size = file.size
            git_file.parent_submission = self.object
            git_file.save(force_insert=True)

            #TODO: maybe centralize this flag setting to happen by the GitFile model
            self.object.files_changed = True
            self.object.save()

            return HttpResponse(status=200)

class SubmissionDownloadFileView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    http_method_names = ['get']
    transition_method_name = 'view_noop'
    model = m.Submission
    parent_model = m.Manuscript
    object_friendly_name = 'submission'

    def get(self, request, *args, **kwargs):
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()

        return g.get_submission_file(self.object, file_path, True)

class SubmissionDownloadAllFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    http_method_names = ['get']
    transition_method_name = 'view_noop'
    model = m.Submission
    parent_model = m.Manuscript
    object_friendly_name = 'submission'

    def get(self, request, *args, **kwargs):
        return g.download_all_submission_files(self.object)

class SubmissionDeleteFileView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    http_method_names = ['post']
    transition_method_name = 'edit_noop'
    model = m.Submission
    parent_model = m.Manuscript
    object_friendly_name = 'submission'

    def post(self, request, *args, **kwargs):
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        g.delete_submission_file(self.object.manuscript, file_path)

        folder_path, file_name = file_path.rsplit('/',1)
        folder_path = folder_path + '/'
        try:
            m.GitFile.objects.get(parent_submission=self.object, path=folder_path, name=file_name).delete()
        except m.GitFile.DoesNotExist:
            logger.warning("While deleting file " + file_path + " on submission " + str(self.object.id) + ", the associated GitFile was not found. This could be due to a previous error during upload.")

        self.object.files_changed = True
        self.object.save()

        return HttpResponse(status=200)

class SubmissionDeleteAllFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    http_method_names = ['post']
    transition_method_name = 'edit_noop'
    model = m.Submission
    parent_model = m.Manuscript
    object_friendly_name = 'submission'

    def post(self, request, *args, **kwargs):
        #print(list(g.get_submission_files_list(self.object.manuscript)))
        for b in g.get_submission_files_list(self.object.manuscript):
            g.delete_submission_file(self.object.manuscript, b)

            folder_path, file_name = b.rsplit('/',1)
            folder_path = folder_path + '/'
            try:
                m.GitFile.objects.get(parent_submission=self.object, path=folder_path, name=file_name).delete()
            except m.GitFile.DoesNotExist:
                logger.warning("While deleting file " + b + " using delete all on submission " + str(self.object.id) + ", the associated GitFile was not found. This could be due to a previous error during upload.")

        self.object.files_changed = True
        self.object.save()

        return HttpResponse(status=200)

#Used for ajax refreshing in EditFiles
#TODO: Probably no longer be needed with list rewrite
class SubmissionFilesListAjaxView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericCorereObjectView):
    template = 'main/file_list.html'
    transition_method_name = 'edit_noop'
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return render(request, self.template, {'read_only': self.read_only, 
            'manuscript_display_name': self.object.manuscript.get_display_name(), 'files_dict_list': self.files_dict_list, 'file_download_url': self.file_download_url, 
            'file_delete_url': self.file_delete_url, 'obj_id': self.object.id, "obj_type": self.object_friendly_name, 'page_title': self.page_title, 'page_help_text': self.page_help_text})

class SubmissionFilesCheckNewness(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    template = 'main/file_list.html' #I think this is not actually used here
    transition_method_name = 'view_noop'
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        file_path = request.GET.get('file_path')
        if(not file_path):
            raise Http404()
        folder_path, file_name = file_path.rsplit('/',1)
        folder_path = folder_path + '/'
        try:
            new_md5 = m.GitFile.objects.values_list('md5').get(parent_submission=self.object, path=folder_path, name=file_name)
        except m.GitFile.DoesNotExist:
            raise Http404()

        if(self.object.version_id > 1):
            prev_sub = m.Submission.objects.get(manuscript=self.object.manuscript, version_id=self.object.version_id - 1)
            try:
                old_md5 = m.GitFile.objects.values_list('md5').get(parent_submission=prev_sub, path=folder_path, name=file_name)

                if(old_md5 != new_md5):
                    #Same file path exists in the previous version. New version of file has dififerent md5
                    image_base64 = "iVBORw0KGgoAAAANSUhEUgAAArwAAAK8CAYAAAANumxDAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAeGVYSWZNTQAqAAAACAAFARIAAwAAAAEAAQAAARoABQAAAAEAAABKARsABQAAAAEAAABSASgAAwAAAAEAAgAAh2kABAAAAAEAAABaAAAAAAAAAEgAAAABAAAASAAAAAEAAqACAAQAAAABAAACvKADAAQAAAABAAACvAAAAAB0W70fAAAACXBIWXMAAAsTAAALEwEAmpwYAAACaGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS40LjAiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgICAgICAgICAgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICAgICA8dGlmZjpSZXNvbHV0aW9uVW5pdD4yPC90aWZmOlJlc29sdXRpb25Vbml0PgogICAgICAgICA8ZXhpZjpDb2xvclNwYWNlPjE8L2V4aWY6Q29sb3JTcGFjZT4KICAgICAgICAgPGV4aWY6UGl4ZWxYRGltZW5zaW9uPjcwMDwvZXhpZjpQaXhlbFhEaW1lbnNpb24+CiAgICAgICAgIDxleGlmOlBpeGVsWURpbWVuc2lvbj43MDA8L2V4aWY6UGl4ZWxZRGltZW5zaW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KJQjh1wAAQABJREFUeAHt3Qe8bVdZL+yENEoIPUAoCaH3UATkAgYsgKggSFMRxQLKRUH5EAsI6sXCVVFABUQRCyrIFRQUFamCCMGEDlISwCSUQAo1CfD9X3O2bE72PnuVMeea5Rm/33v2PmvNOcY7nlnW2GvNNeZBBykECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIDAPAUOnme39ZoAgY4F6txyjcTVE0cm6v/nJU7fF1/JT2W+ArU/HJOofaT2j9ofPpOwfwRBIUCAAAECBIYrcEJSe1LitYnPJmoQs1Ock8dfmfjZxA0TyjwEbpxu/lziXxLnJnbaN7YGvq/J809M3DyhECBAgAABAgQ2KnBoWv/+xMmJ3QYwez3+r1n3vol610+ZlkBt0+9KvDGx136w2/MnZd2HJA5JKAQIECBAgACBXgXumdbem9htoLLs4zWw+cZee6CxLgVqW741sex+sNvy70ldd+8yYXUTIECAAAECBLYE6prL5yV2G5is+/g/pO5bJJRxCtS2q2247n6w2/rPTd2XHieNrAkQIECAAIExCBybJN+e2G0w0urxL6WN5yWumVDGIXCtpPnHidp2rfaD3eo5JW1UewoBAgQIECBAoKnA9VLbRxK7DUK6ePzzae9XE5dLKMMUqG3za4naVl3sA7vVeVraOz6hECBAgAABAgSaCFwttXwosdvgo+vHP5m2H504PKEMQ6C2xWMStW263v671f/BtH10QiFAgAABAgQIrCVQMzHUTAq7DTr6fPwDyeNBCTM6BGFDpewfnKjBZp/bfre2ahq82kcVAgQIECBAgMDKAk/KmrsNNjb1+JuT04kJpV+Bu6a5st/Udt+t3Sf0y6A1AgQIECBAYEoCdWOI8xO7DTQ2/fjfJbebTgl8oH25WfJ6eWLT23u39r+Y3K4/UDtpESBAgAABAgMX+Ovkt9sgYyiPX5gc/yBRt6pV2grUrX//MNHHzAvr7k8vbNt1tREgQIAAAQJzEKh3Tr+cWHcg0tf6dTvjX04clVDWEyjDpyQ+l+hr+63bTu2rN0koBAgQIECAAIGFBf4kS647CNnE+h9P3o9KHLZwTy24JVBmP574RGIT227dNp+/1RE/CRAgQIAAAQJ7CRyXBS5IrDsA2eT6/5n8759QFhN4QBZ7f2KT22zdtmufPS6hECBAgAABAgT2FHhmllh38DGU9d+Yvtxpzx7Pd4G7pOtvSgxle62bxzPmuyn1nAABAgQIEFhU4KpZsO+7Zq07yFlk/ZekXzdaFGEGy9X1ri9NLGI3pmXquuOjZ7D9dJEAAQIECBBYQ6Bu5TumAc4yudaMDs9K1J3j5lquno4/J1EWy9iNadn6wp1CgAABAgQIENhR4HJ59JzEmAY3q+T6mfTxyYkjE3Mpl01HfylRs1msYjamdc5OH83WEQSFAAECBAgQuLjAz+ahMQ1s1s31zPT3RxNTvjVt9e2RiY8l1vUa0/o/k/4qBAgQIECAAIGvEbhU/ldTenUxqBn6fK7vSb+/82s0pvGf+6Ub7010sU1b1fm+jvKrAX7t0woBAgQIECBA4H8Eau7aVoOY7fXU7X+vkXhuYuh37Hp9cvz6xNjL/0oH3pDYvh2G9nu9u/7wxCGJ2ke6yK/e2VYIECBAgAABAv8tUDccOC3RxaDjjtuMb5bfX9ZROy1zr1sqX39b3mP59YZJ9G8SLS1a17XT9dM1QG/dTtV3amLKl6ukewoBAgQIECCwqMBDs2AXA47X7JLAXfP4mztqs1U/Lkh+NR/xGKa4qqnkfj9RObfqf+t6alaI5yRqloidymvzYOs2q76H7NSYxwgQIECAAIF5CVwi3X13oovBxj0OQHlwnntw4oMdtd2qP+cmvycmLpMYWqmcnpQ4L9Gqv13UU+/q3zRxoHLPPNlF2+9MvbWvKQQIECBAgMCMBe6bvncx0HjrgqaHZ7nHJM7qKI9WfTs9+f1Ioq453XSpj+kfkTgj0ap/XdRzUvK7W2LRUvtMF3ncZ9EELEeAAAECBAhMU6CrSwvuvyTX5bP8ryaGfpe3dyXH71iyby0Xr8FbV+/ItxpsnpYcvzex7DurD8g6rXLYXs+bUq9CgAABAgQIzFTgm9Lv7QODVr/XVFh1qcQq5VpZ6XmJoc/o8JrkeLtEX+UOaeh1iVbbqIt6zk5+j0tcMrFKqX2mq2nKlnmneZXcrUOAAAECBAgMVOBfklcXA58fbNDfW6SOf+gov5Z9/qvkeN0G/d2tipot4kWJljm3ruv85Pe0xJUS65YfSgWt86v6/mndxKxPgAABAgQIjE/g9km5i4HFR1JvXZfbqtS70F1d29mq/zXg+53ElVt1OvUcnahZIoY880L5tR7w177z0USrbbO9ntumXoUAAQIECBCYkcDfpK/bBwOtfn90B4Z1LWhdE3pqolWeXdRzTvL75cTVEquWY7LirySGPvPC65NjXWbRRfnJVNrF9nlxF8mqkwABAgQIEBimQE0R9eVE60HFJ1NnTZXVVTkiFT828alE69xb1lfv+L408f2JuiZ5r3LtLPCwxN8lhv6Obl2f3fVtmGsfqn2p5Tapumqfv3FCIUCAAAECBGYg8CfpY+vBRNX3xJ7srpB2/m/iC4ku+tG6zo8lz/qS218knr0v6vfXJj6eaN1eF/VVno9MHJroo/xCGumiH8/rI3ltECBAgAABApsVOC7Nd/Eu4rmptwaifZZj01gN3rt4t7qLwdYY6/xcfP9P4qhEn+WKaayLyzrq3fd6R10hQIAAAQIEJixQX4TqYuD11A2a3Spt17fwu+jXXOusaeH+KHHNxKbKb6ThLvx/Z1Md0i4BAgQIECDQvcBV00QXN3aoSwuu3n36e7Zw9yxxSqKLQdKc6nxFDG+xp3b3C1wjTXwx0dq+3rW+Svfpa4EAAQIECBDYhEDdyaz14KHqe9YmOrNLm3XzgocmPpzooq9TrvPkmH1LYkjlOUmmC/O6TEMhQIAAAQIEJiZwufTnnETrwcOFqfP4AVrV3b5+OnF2onWfp1ZfzXv7/Yn6Y2Fo5XpJqPax1ua1X/R9XfLQbOVDgAABAgQmJ/Cz6VHrQUPV9+cDl6q7f/1moouPxrvw7LPO+gOo9otLJYZcakaLLlzqDyKFAAECBAgQmIhADWi6mP6qZke4+UiMrpM8a3BuRoeLZul4RizGch3rCcm1iwHvmam3PglQCBAgQIAAgQkIPCp96GLA8LcjtLlNcv6Xjjy6MG5d54vT9xuMcLu9vKNt9qMjtJAyAQIECBAgsJ/AYfn/aYnWA6eq7477tTWm/35rkn17oguXIdb5xvT1f41pA+2X65072lYfTL193Uxjvy75LwECBAgQINBK4KGpqIsBWN05bOylvqT1sER9aasLoyHU+f707bsSUyivTye6MP3eKeDoAwECBAgQmKtADejenehikHCPCaHWNc715a0uZrHown6ROj+Z/vxEot7hn0q5VzqySN+XXeYdqffgqSDpBwECBAgQmJvAfdPhZV/8F1n+pIlCXjn9qrtwnd+R2yK26y5TNxb5tURNQzfFUnMFr2u00/rfMUUsfSJAgAABAnMQeHM6udOL+7qP3X/ieNdN//6yI7t17Xdbv2af+JPEtRNTLg9K53YzWOfxusZZIUCAAAECBEYm8E3Jd50BwG7rvjf1DvEGBV1sntul0rpWeTeLoTz+z8nxVl0ADLDOQ5JTXZfchf1dB9hfKREgQIAAAQIHEOhq6q36ktfcyrenw3WdZxeDrHXqPCU51WwTcys/kg6v47bbuv84N0j9JUCAAAECYxa4fZLf7UV9ncc/knqn9CWoZbZxvav9wMR/JNYxbLFuXUNdMy/M9YtWR6Tvp3e0HWqeZoUAAQIECBAYgcDfJMcWA6v963j0CPreR4onppEXJOoLYvsbdfX/z6WtP0vUfLTKQQc9NghdWL8ILgECBAgQIDB8gZsmxfoCU+vBwCdS52WG3/1eMzwqrX1fov7AOC/R2vzc1Fl3Rqt5Yi+bUL4qcGR+/VSitfmXUucNv9qM3wgQIECAAIEhCtQ39VsPAqq+JwyxswPKqS71uFPipxMvTLwncUFi0W1Ry7478VeJ/y9Rd0Wb6+Uj6fpC5Rez1KK+yyz3hwu1biECBEYjMNfrv0azgSRKYEmB47L8fyZa3yq13r08NvHphLK4QG2HayaOSdQcv/UubV1/WuWLiXKtG0TU9agfTVyYUBYXuFIWPS3R+pOH+uPjuom6Zl0hQIAAAQIEBibwzOSzzDtZiy771IH1UzoEtgR+K78suh8vs9xvbzXgJwECBAgQIDAcgasmlS6+RPWF1Hv14XRTJgS+RqDeQa93y5cZzC6y7GdTZ70rrxAgMAGBuUweP4FNpQsE9hR4TJa45J5LLb/A87LKGcuvZg0CvQjUpSB/2kFLl06dP9FBvaokQIAAAQIEVhS4XNY7J7HIO1fLLFPXlB6/Yk5WI9CXwA3SUM2usMy+vciydc262TH62oraIUCAAAECewj8bJ5f5AV82WX+fI92PU1gKAI1M8ay+/ciyz9uKB2UBwECBAgQmLPApdL5jycWefFeZpmay/fmc4bV91EJ3DrZLrN/L7psXc7TxaVCo8KVLAECBAgQ2LTAo5LAoi/eyyz3t5vumPYJLCnwD1l+mX180WUfsWQeFidAgAABAgQaCtSNCWoe0kVfuJdZ7o4N81QVgT4EviGNLLOPL7rsB1LvIX10QBsECBAgQIDAxQUemocWfdFeZrnXXLwpjxAYhcAbkuUy+/qiy373KHovSQIECBAgMDGBmlawbkW76Av2MsvdfWJWujMfgW/v6Jh4e+p1d9L57Ed6SoAAAQIDEXhI8lhmELvosicNpH/SILCKQA1Ka3C66P6+zHIPWCUh6xAgQIAAAQKrCVw2q9WE+8u8WC+67P1XS8laBAYj8D3JZNH9fZnlTk29dUMKhQABAgQIEOhB4DlpY5kX6kWXfU/qdQfGHjagJjoVqC+YfTCx6H6/zHJP7zRzlRMgQIAAAQL/LfC9+XeZF+hlln0YYwITEaipxJbZ95dZ1qUNE9lJdIMAAQIEhilw16T1hcQyL86LLvuR1FvTnCkEpiBwRDpRN41YdP9fZrnPpd47TQFJHwgQIECAwNAEvjEJfSaxzAvzMss+emgdlg+BNQXqtsDLHAPLLHtO6r7zmvlZnQABAgQIENgm8EP5/fzEMi/Iyyz7idTtyzjbwP06CYH6cuenE8scC8ssW5+2fN8kpHSCAAECBAhsUOBKafvPE8u8CK+y7BM22EdNE+hS4JdT+SrHxDLr/HHauEKXnVA3AQIECBCYokBdf/gTibMSy7zwrrJsvQN2+YRCYIoCV06nurwUaOuY+3ja+bHE4VNE1CcCBAgQINBS4Hqp7MmJMxNbL6Rd//z5lh1QF4EBCvxacur6ONqq/7/S1hMT1xmgg5QIzFbg4Nn2XMcJbFagjr1jEvWieMPEbRLfkLhJos9SA+vrJ+odMIXAVAXqcoP3J67YcwffkfZek3hr4n2JDyVOT9TgWCFAoEcBA94esTU1O4F6ca0BbcXx236v/x+bqMsWNl0emgSev+kktE+gB4FHpo1n9NDOXk3UF91OS9Tgd6f41F4VeJ4AgeUFDl5+FWsQILBPoGY1qMHrbnHUwKVel/y+IfGVgecpPQItBOoOgm9K3LZFZR3WUdOd7TQQ3nrs8x22rWoCkxUw4J3sptWxBgKHpo5rJ/Z/d3ZrgHt0gzY2VcVn0/AtEx/YVALaJbABgZunzTcnhvDpyqrdr8uQtga/23/WrZTr5jFfWrVi6xGYsoAB75S3rr7tJVD7/9UTWwPY/X9eM88dslclI33+R5P37480d2kTWEfgJ7Pyb6xTwYDXvTC51aB3+0C4fq/BcP38WEIhMEsBA95ZbvZZdXr7dbT7D2iPjcQlZ6VxUWdrXt/vmWG/dZlACdTr3t8kvqP+M7NSt0Q+NbF9QLw1GK7Hzk0oBCYpYMA7yc06q07VdbTHJfYfzG79/3Kz0ti7s2/LIl+fqBc+hcBcBer6+n9L3HiuALv0u74wt30wXL9vDYhPy+9f3GU9DxMYvMDBg89QgnMXqH30uMRu19Fede5AS/S/PuqswW7NE6oQmLvAdQLwxoRzyGJ7wleyWE2ptn1AvDUYrp91XqllFAKDFDDgHeRmmX1St4vAtye+MXGLxGUSynoCn8zq35B413rVWJvApAROSG9elXCnwfU3a30R9j8Sr07UJSMnJRQCBAgQ2E/g8Py/bsv5zkS9SyDaGXwinvXtdIUAgYsLfF0eqo/ynXPaGtS5/EcSdW5XCBAgQCAC9098KOEFp73BaXHt++5taVIhMCqBmqLvjIRzUHuDOrffb1R7g2QJECDQWKBu9/nChBeZbgzq48Wadk0hQGBvgWOzyNsTzkfdGNS53peI994PLUGAwMQEbpj+1L3lvbh0Y1C3C77UxPYZ3SHQtcCRacAf4d2ck+pcX+f863e9EdVPgACBoQjcLInUdaUGu+0NzovrDw9lQ8uDwEgF6vsENXWfc1R7g7r5xU1Hul9ImwABAgsLHJcl64TnhaS9wSvjWlMtKQQIrC9wg1TxmoRzVXuD0+N67fU3kRoIECAwTIH6iL2uK/UC0tag5td94DA3uawIjFqgpu78vkQN0Jy32hq8NaZzvNNluq0QIDB1gaelg1402hnUO+WPSdQfEgoBAt0J1B0dH5+o+aydw9oZ/GZ3m0zNBAgQ2IzA7dPslxJeLNY3eHccH5GoF2GFAIH+BC6Tpn488Z8J57L1Deo14TYJhQABApMReFV64gVidYNPx+85ibsk6mNWhQCBzQnUMXi3xB8lzk44t61uUN89UAh0LuCFs3NiDUTgTonXkVhK4IIsfXLiNYmXJV6fuDChECAwLIHDks6JiXvs+3nL/DwkoSwucMcs+sbFF7ckgeUFDHiXN7PG8gJ/mlW+Z/nVZrHGOenlh/bFB/KzLld4V+KUxOcTCgEC4xKoS41OSNT0izXTw/GJ4xLXSVw+oVxc4E/yUH05UCHQmYABb2e0Kt4nUF+oOisx1y9WfSF9PzWxNajd/2ddqqAQIDAPgculm8clavBbP7di6/9H5bE5ls+m01dO1PlSIdCJwMGd1KpSAl8V+Nb8Wh/JT7XUly4+mth/ILv1/zPy3Fem2nn9IkCgqUDdbn1r8Htcfq/Y/v+6E9xUyz3TsX+Yauf0a/MCh24+BRlMXODOE+jfx9KHrQHs/j9rDty63lYhQIDAugL1iU9FzVG7U6l3QY/bFtsHw/X4mGduqdcKA94gKN0IGPB246rWrwrc8qu/Dva3c5PZ/gPZ7f+vW4wqBAgQ2LRAzQNc8ZZdEjk6jx+3L/YfDNfjQ77Rwy2Sn0KgMwED3s5oVbxPoE66my5fTAKnJrYPYrf//qlNJ6h9AgQINBD4eOqo+Pcd6jo4j101cVxi/8Fw/b9u9XtEYlOlvtynEOhMoA4AhUCXAnXyvUqXDaTuLycOdB3t1m1BO05D9QQIEBitQI0Hrp7YaTB8XB6vAXFNwdZVqdeKGpArBDoRMODthFWl2wRq2q1W3zyueWhflNj+7mz9/uGE62iDoBAgQKAjgUuk3mMSWwPim+X3xzVsq14rTNvWEFRVBAj0K1B/tX+lUdQ7ua0Gz/0qaI0AAQLTErhLutPq3F711GuFQqAzgfqLTSHQpUDNwduq1CcSY/gSXKv+qocAAQJDFaiba7QsLV8rWualrokIGPBOZEMOuBsfbJzbrRrXpzoCBAgQWF6g9YD3tOVTsAaBxQUMeBe3suRqAu9dbbVd12p9kt21IU8QIECAwK4Crc/FdUt1hUBnAga8ndGqeJ/AKY0lvMPbGFR1BAgQWFKgZmu4yZLr7LX4yXst4HkCBAgMWaCuuW35xYbzU9/hQ+6w3AgQIDBxgZunfy3P61WXG09MfKfZdPe8w7vpLTD99utjqhqktir1zsJNW1WmHgIECBBYWqD15Qx1c6B3L52FFQgsIWDAuwSWRVcSqPlxW5/IWp9sV+qYlQgQIDBTgdbn4HpjxFzqM92Z+uq2AW9f0vNup/W1Wa7jnff+pPcECGxWoPWAt/VrxGZ1tD5IAQPeQW6WySXV+mRmwDu5XUSHCBAYkUDr+dBbv0aMiFKqfQkY8PYlPe92Wp/M6mTrttjz3qf0ngCBzQhcK81eqXHTrWfzaZye6ggQILCYwOWzWOtv9F5vsaYtRYAAAQINBb49dbU+n1+uYX6qIrCjgHd4d2TxYGOBs1Nf67vouKyh8UZSHQECBBYQaH05w6lp85wF2rUIgbUEDHjX4rPyEgKtL2s4YYm2LUqAAAECbQRan3tbvza06aVaJidgwDu5TTrYDrU+qXmHd7CbWmIECExYwIB3wht3yl0z4J3y1h1W31p/KcGAd1jbVzYECExf4LLp4vGNu9n6zZDG6amOAAECywlcJ4u3/qLDVZdLwdIECBAgsIbAnbJu6/P4sWvkY1UCCwt4h3dhKguuKfChrN/6iwne5V1zo1idAAECSwi0vpzh02m79Real+iOReckYMA7p629+b66rGHz20AGBAgQWFWg9YC39WvCqv2y3gwEDHhnsJEH1MXW12q1PvkOiEoqBAgQGJxA6ynJWr8mDA5MQsMRMOAdzraYQyatT24uaZjDXqOPBAgMQeCQJHGzxom0fk1onJ7qCBAgsJpADVBbfuHhy6mvvjWsECBAgEC3AjdN9S3P31VX63eMuxVQ+6gFvMM76s03uuTflYwvaJj1wanLCbMhqKoIECCwi0DrS8jOTzv1mqAQ6EXAgLcXZo3sE/hifr6nsUbrk3Dj9FRHgACBSQi0Pte+Oyot3wCZBLJOdCdgwNudrZp3Fmh9zZbreHd29igBAgRaCrQe8LZ+LWjZV3VNUMCAd4IbdeBdan2SM+Ad+AaXHgECkxBofflY69eCSSDrRHcCBrzd2ap5Z4HWJ7n6IsVhOzflUQIECBBoIHBM6rhKg3q2V9H6tWB73X4ncDEBA96LkXigY4HWJ7nDk+9NOs5Z9QQIEJizwAkddL71a0EHKapySgIGvFPamuPoy6eS5kcap+qyhsagqiNAgMA2gdYD3rqd8Nnb6vcrgc4FDHg7J9bADgKn7PDYOg+1Phmvk4t1CRAgMDWB1ufYk6cGpD/DFzDgHf42mmKGrU923uGd4l6iTwQIDEXAgHcoW0IeKwsY8K5MZ8U1BFoPeOtkXDehUAgQIECgrcCRqe66bas8qPVrQOP0VDdFAQPeKW7V4fep9cnuqHT5OsPvtgwJECAwOoFbJOPWY4XWrwGjQ5Vw/wKtd+L+e6DFMQp8MEmf2zhxlzU0BlUdAQIEIlCfoLUsZ6eyU1tWqC4CiwgY8C6iZJnWAl9JhW9rXKkBb2NQ1REgQCACrW840fpLyzYSgYUEDHgXYrJQBwKtP9Jq/S5EB11WJQECBEYn0Prc2vrcPzpQCW9GwIB3M+5aPaj5lxa8w2uvIkCAQFuBQ1LdzdtWeZB3eBuDqm4xAQPexZws1V6g9Umvbn15dPs01UiAAIHZCtwgPb9U4957h7cxqOoWEzDgXczJUu0F3pEqL2xcbeuP3hqnpzoCBAiMSqD1OfWC9P6doxKQ7GQEDHgnsylH15EvJOP3Ns7aZQ2NQVVHgMCsBVoPeN8dzfNnLarzGxMw4N0YvYYj0PqjLQNeuxUBAgTaCbQe8LY+57frqZomL2DAO/lNPOgOtj75GfAOenNLjgCBkQm0npKs9Tl/ZJzS3aSAAe8m9bXd+uR3vZBeBisBAgQIrC1wtdRw1bVr+doKWp/zv7Z2/yNwAAED3gPgeKpzgdYnv9qfW78j0TmCBggQIDBAgRM6yKn1Ob+DFFU5VQED3qlu2XH065NJ8/TGqbqsoTGo6ggQmKVA6wHvh6P46VlK6vQgBAx4B7EZZp1E67/4W5+kZ71xdJ4AgdkKtD6Xtj7Xz3bD6PhqAga8q7lZq51A65Ogd3jbbRs1ESAwXwED3vlu+0n23IB3kpt1VJ1qPeC9WXp/6KgEJEuAAIFhCVw66Vy/cUqtz/WN01Pd1AUMeKe+hYffv9YnwSPS5RsPv9syJECAwGAFbp7MWo8PWp/rB4snsWEKeCdsmNtlTlm9P539TOLIhp2uyxre3rA+VREYk0ANVOrcfsiGf/5J2j8joYxP4ITGKZ+T+k5tXKfqCBAgMDqBf03GX2kYvzU6AQkTaCNw11TT8lhata76g7P1O4RthNSyiMDvZaFVt/1O6712kUYtQ6BLASekLnXVvajAKYsuuOByrd+dWLBZixHYqMDBaf0XN5rBVxt/Qn798lf/67eRCbQ+h7qcYWQ7gHQJEOhG4EdS7U7vCqz6mLkeu9lOah22wDc1Po5WPf7ekjxq8K2MU6DeCKvLzFbd/jut97BxUsiaAAECbQVul+p2Okmu89h12qaoNgKDFqgB5hsS6xwzrda9x6ClJLeXwA072I9uvVejnidAgMAcBC6VTl6YaPWCW/XcZw5w+khgn8Dd87Pl8bNqXa9PHt7dHfdu+YDG+9L5qe+IcZPIfgoCruGdwlYcfx8+ny68r3E3TE3WGFR1gxWoAeaTB5LdzyePGiwr4xWoucxblveksi+2rFBdBFYRMOBdRc06XQi0/lJDfSynEJiDwD3TydsPoKOvTA6vHkAeUlhP4AbrrX6xtVuf2y/WgAcILCJgwLuIkmX6EGh9Ujy2j6S1QWDDAkN6d7dmZlDGL3Bc4y60Prc3Tk91cxEw4J3Llh5+P1vfKOJqw++yDAmsLXCv1HDbtWtZv4KXpYo3rl+NGgYg0Prc2XrayQEQSYEAAQKrC9R921f9osxO631y9VSsSWAUAvXu7kmJnfb/vh/zLfxR7DILJXle433q2gu1aiECBAjMROCo9LPli/RnZ+Kmm/MVuHfjY2bV4+9F890Ek+x53TBk1X1hp/UOn6SSThEgQGBFgUOz3k4ny1Ufq2nOFAJTFajL0erayFWPj1br1eDoplNFnmG/nIdnuNF1mQCBfgVqnsZWL8JVzwX9pq81Ar0K3DettTxeVq3rT3vttca6Fjik8X7l9tJdbzH1EyAwOoGjk/GqL7o7rVfXoSkEpihQ7+6+LbHTft/nY/UpSl17r0xLoPVNgC43LR69GauAWRrGuuWml/e1GnfJNbyNQVU3GIF6d/fmA8jmecnhPweQhxTaCpzbtrqDrtm4PtURWEnAgHclNit1IHCTxnWe2bg+1REYgkCds580gETqkqFfGkAeUmgvcFbjKluf2xunp7q5CBjwzmVLD7+fd2ic4hmN61MdgSEI3D9JDOFLYs9OHqcNAUQOzQX+q3GNrc/tjdNTHQECBPoVqI9GW15/+Mx+09cagc4F6gtF70q0PE5WqevzyeGYznurgU0J/GEaXmW/2G2d1jcV2pSLdkcu4B3ekW/AiaR/QvpxvcZ9eXfj+lRHYNMCD0wCN950Emm//pg8fQB5SKEbgfc0rvZmqe9GjetUHQECBEYp8Ixkvdu7A6s+fuIoJSRNYGeBene3BiKrHg+t1vtMcrjKzil6dCICd08/Wu0vW/U8dSI2ukGAAIGVBerFs15Et06MLX7WF2ous3JGViQwPIHvTUotjo116/jl4dHIqLHAlVJf67utnZ06TU/WeEOpjgCBcQn8VtJd90V4//VPGheBbAkcUODQPNv6Gvf9j5lF/l+DliscMFNPTkXgnenIIvvEMss8ZSo4+kGAAIFlBW6RFerd2GVOmoss+yvLJmJ5AgMWeGhyW2S/73qZnx+wkdTaCvx2B/vcF1Kna3nbbie1ESAwAoFLJsdTEl28SN9lBP2XIoFFBA7LQu9PdHGcLFPnJ5PDZRdJ2DKTEPjm9GKZ/WPRZd+ceg+fhJBOECBAYEGB52e5RU+SyyxXN5yoL/goBKYg8LB0Ypn9v6tlHzsFTH1YWKD+0KobUHSxP9UczgoBAgRmIfCr6WUXJ9Kqs64JVghMQaAGHR9MdHWsLFpv3cTl0lMA1YelBJ6VpRfdR5Zd7klLZWJhAgQIjFCgy8FunXRvOUITKRPYSeCH8uCyA4kuln/UTsl5bPICt+94/zPjx+R3IR0kME+Bg9Pt30108YK8Vedr50mr1xMUqOsc69a9W/v2pn5+ODkcMUFfXVpM4C1ZrMt9r74cV68NCgECBCYhUNfUdnXN7vaT8X0noaUTBA466OFB2L5vb+r3H7YxZi3w3T3sh3UrY9+7mPVupvMEpiFQ71S9ONH1C/bb0oZ3Cqaxz8y9F/WOar2z2vUxs1f9H0gOdR2xMl+BGoj2MQf0X6Ud+9p89zM9JzB6gfqiyysSe72wtnj+fqPX0gECFwn8WH60OCbWreMhNgiBCHxPT/vjy9POpYgTIEBgbAJ1G8nXJdZ90V1k/WpHITAFgZqf+qOJRfb7Lpd5d3LwMfMU9qj1+1CfnHV9Le/WvvzqtGW+5/W3mRoIEOhJ4Mpp56TE1kmsy59fSjsn9NQvzRDoWuB/p4Euj5dF675/1x1V/6gE7pBsv5xYdP9ZZ7l/TztXHJWOZAkQmKXAMel1F/dh3+0E+tRZKuv0FAXq49zTE7vt6309fnJyuMQUgfVpLYFnZu2+9sG3p62rrZWtlQnsJ+BLPvuB+O9aAtfJ2v+cOH6tWhZf+V1Z9NaJLy6+iiV7ErhT2nl0T21NpZmj05E7D6Az9QfrezaQx2+kzTduoF1NLiZwmSxWfwxdb7HF116qviz3TYn6AqdCgACBwQjcOJn0ee3h59LeLQbTe4nsL/CgPNDXu0HamYb1d+2/E/n/4AS+LhnVGwx9HXM12L3B4BQkNEoBH1uNcrMNLulbJaPXJK7RY2b1TfaaikwhQIAAgX4E3pxmHtNPU//dyrXy72sT3tzoEX2qTRnwTnXL9tevO6apVyWu0l+TB/1W2npej+1pigABAgQuEvjd/HhWjxhXTVuvTtStjhUCKwsY8K5MZ8UI1PVV/5ioKcj6Kn+dhn6qr8a0Q4AAAQIXE6jZRP7uYo9298AVUnV9P+Su3TWh5qkLGPBOfQt31797p+o64dUXGfoqL09DW5Og99WmdggQIEDgawUuzH8fkKhP9/oqR6aheg24V18NamdaAga809qeffWmBp0vStQtUPsqf5+G7pswI0Nf4tohQIDA7gKfz1Pflqh3XvsqdWOW/5eowbZCYCkBA96luCwcgYcnnp84tEeNF6et+yQMdntE1xQBAgT2EPhcnq9B70v2WK7l04elshckfrBlpeoiQIDAdoHH5j99TUez1c4fp023ON2+Fcbxu2nJ+j9Wto6Zsf40Ldk4ju2dsqw3QP4k0ee+V3d+M9f3TlvDYwQIrCXwS1m7z5NZtfWMxMFrZW3lTQkY8PZ/vPR9fLZuz4B3U0drm3brXN3n3di29r8ntklfLQQIzF2gTmJPS2ydXPr6+Stzhx95/w14+z9m+jo2u2rHgHfkB/2+9J+Sn13tI7vV+9Rp0OkFAQKbEqhrvJ+b2O0k09XjP7OpDmu3mYABb//HTVfHY1/1GvA2O/w2XtHjkkFf+81WOzU3sO8lbXzTS4DA+ATqiwF/mdg6mfTxs67JeuT4qGS8g4ABb7/HTh/HZ9dtGPDucCCN+KFHJPcvJbreb7bX/2dpr88vVI9480idAIESqKlfXpbYfiLp+vea1/GhCWUaAga8/R4/XR+ffdRvwDuNY397L747/7kg0cf+s9VGzRjR55SZ2/vr9wELePt/wBtnQ6ldNu3WnLff2mP756etByZqRgaFAAECBKYh8OfpxncmvtBjd74jbdUbNn3eFKnH7mlqVQED3lXlprne1u0bT+yxezV5ed21rW4ZrBAgQIDAtAT+Lt2pN1A+02O3vjFt/VPi8j22qamBCxjwDnwD9ZjeVdPWaxK367HNc9PW3RP/0GObmiJAgACBfgVeleZqEPqpHpv9+rRV7V6lxzY1NWABA94Bb5weU7t22npd4uY9tnlW2qoTYLWrECBAgMC0Bf493fuGxJk9dvOEtPXaxDV7bFNTAxUw4B3ohukxreunrRp01s++yhlpqE58b+mrQe0QIECAwMYF3pEM7pQ4tcdMbpS26jXu+B7b1NQABQx4B7hRekyp3tGtE0G9w9tXOTUN3Tnxzr4a1A4BAgQIDEbgA8mkXgPe02NGx6Wteq27SY9tampgAga8A9sgPaZT1+rWNbt17W5f5b1pqE50dcJTCBAgQGCeAh9Nt+u14K09dv+YtPXaxG16bFNTAxIw4B3QxugxlRPT1isTNStDX+XkNHSXRJ3oFAIECBCYt8An0/27JV7fI8OV0ta/JOqyCmVmAga8M9vg6W5ND/PyxJE9dv2NaeuuiY/32KamCBAgQGDYAuckvZqp5xU9pnnUvvaqXWVGAga8M9rY6eoDEn+TuFSP3a53kr85cXaPbWqKAAECBMYh8LmkWTeLeFGP6V46bb00cd8e29TUhgUMeDe8AXps/mFp6wWJw3ps82/T1r0Sn+2xTU0RIECAwLgE6m6bdTvyP+ox7cPT1l8lvq/HNjVFgEDHAj+R+r+c+EqPUbeUPDShzFOgXrz63N+0NX7v75rnoaLX2wQOzu9PS/R5PNdr449ty8GvBAiMVOAJybvPk0e19eyETw9GusM0StuAt//jru/jvHV7BryNDr4JVPOk9KH1/rVXfY+fgJsuEJitwK+n53sd5K2f/43Zauv4dgED3v6PvdbHct/1GfBuP4L8/pgQ9P3J5K9gJ0BgXAL17urvJ/p+wfqFcTHJtkMBA97+j7++j/fW7RnwdnhAjrTq+u7JlxKt97UD1ff0tFeXVigECAxcoK6b/dPEgQ7oLp6rv8YVAlsCBrz9H4NdHNd91mnAu3X0+Lld4P75T32prc998Xlp75CEMiEBf8VMaGOmK/Wt079M3KfHbtVHTg9P/EGPbWpq+ALXSoq3H36aTTM8IrU9N1E/N1nelcZ/YZMJrNj2v2W9j664rtWmLXDPdO+vE31OqVntPThxQUIhQGBAAvXXaM2x2+dfwVtTyQyIQSoENibwyLTc5/G3W1vfuTEBDRPoTuDOqbpuVLHbft/F4y9Me76A3d02VTOBlQSekbW6OOB3q/Pzae/bVsrUSgSmJ1AT2Z+R2O146evxk5KDT+6mt3/p0UUCt8mPTyT6Op6qHV/EvsjevwQGIfDAZNHnCeC8tHe3QfRcEgSGIfBTSaPPY3C3tuqjX4XAlAVunM7VpS+7HQNdPN7nZYJT3nb6RmAtgatk7bMSXRzkO9X5qbR1h7UytjKBaQlcNt3p+12nnY7Nf00e3t2d1r6lNzsLHJeH35/Y6Tjo4rGPpa0rJBQCBDYo0Of0Y3XQ33KDfdU0gSEK/FyS6uJFdtk67zpEHDkR6Ejg6qn3HYllj5NVl//tjvqhWgIEFhA4NsvUN0hXPYCXWe/DaecGC+RkEQJzEqh3fc5OLHMsdbHsK+eErq8E9glcMT//PdHFMbV/nV9MO8fsa9cPAgR6FujrTmr/mX4d23PfNEdgDAK/lCT3f2HcxP/vOAYsORLoQKAuKXpVoo/j7pc7yF+VBAjsIVDTkJ2Z6Pogf3vauNoeuXiawBwF6vr5+gJn18fgXvW/bI74+kxgm8Al8/vfJvY6VtZ9/iNpw3Xy2+D9SqAPgTulkXUP3r3Wr4+K6iMjhQCBiws8NQ/tdQz18fxtLp6aRwjMTuCw9PgFia6PudvOTlaHCWxY4Ilpv8sD+zWpvz4qUggQuLhAfWGm5qLu8hhcpO6/vnhqHiEwW4G6ScSzEoscO6su87jZ6uo4gQ0JvDTtrnrA7rXey1P3pTbUL80SGIPA05PkXsdR18/Xbb1vNgYsORLoWaDL77fU3dcUAgR6FHhv2uriBbUO5vpoSCFAYGeBY/Nw3Va7i+NvmTr/bOf0PEqAQAS6mi7wbXQJEOhX4Nw0t8yL4yLL/lHqrC/DKQQI7C7wnDy1yPHU5TIXJgfTBO6+jTxDoAT+d6I+CWl5LH6yKlYIEOhPoPVB/DtJ3bdP+9t+WhqnwPWSdg02W76ArlLXc8fJJ2sCvQt8X1pc5RjbbZ36dEcZoUBd4K0QKIG3JOoAVwgQ2F3gF/LUpj8FqZvN/NLuKXqGAIF9AjXGqRmNWhavky011UVgAYHWlzTUO8aPXKBdixCYq8BN0vHWn6zs9i7SgR5/5lw3gH4TWEKgq2nKXNKwxEawKIEWAu9JJQd6UVz1ubrQXyFA4OIC9YXOVY+rVuvVVGhub3rxbeMRAtsFurwRxSnbG/I7AQLdC7wkTbR6Ed2/nprSRSFA4KsCt8qv+x8nm/j/b3w1Jb8RILCDwJF57JWJro7Pv9qhTQ8RINChwBNSd1cHdNX7+wnXeHe4AVU9KoE+blu61/H8mYgdPSo1yRLoV+AKae6Nib2OpXWe///67ZLWCBC4YwjWOWgXWffP08ahqAnMXOAO6f8ix0vXy/yfmW8H3SdwIIH6Y/DkRNfH4a0PlITnCBBoL1Dvvp6e6Prgrne26noohcBcBf4pHe/6ONur/rOTQ717pRAgcHGBa+Whrr7Xsv3YPO3iTXuEAIE+BH41jWw/GLv6/VVp57J9dEgbBAYmcGLy6eq4WqbeuoRJIUDg4gI1N/apiWWOp1WX/cWLN+8RAgT6EKi/avu6xem/p60r9tEpbRAYiEDdiOV1iVVfHFutV9MgHTUQE2kQGJLAzZLMGYlWx9qB6qkZUq42pM7LhcDcBJ6RDh/oIG353DvS1tXnBqy/sxW4e3re8vhZtS5fkpntLqjjBxD4ujx3VmLV42rZ9cyQcoCN4SkCfQhcKY18IrHswbvq8u9PW8clFAJTFqh3d9+cWPU4abXemcnh0lOG1jcCKwjcJeu0vvnSgY7Zehf5civkaRUCBBoL3C/1Hehgbf3cR9PejRv3QXUEhiRw7yTT+rhZpb5HDQlFLgQGIHDP5PC5xCrH06rrfNsA+i0FAgT2Cfxmfq56MK+yXr2rbHoWu98UBWoGlLclVjkuWq7z4eRwxBSB9YnAigLflfW+mGh5nO1VV305XCFAYEAC9SL9osReB2/L589Je3cekIFUCLQQeGAqaXmcrFrXD7fojDoITETg+9OPCxOrHk+rrFdz0dflTQoBAgMTOCz59D3orY+W6iMmhcAUBOpGK33M57nXi+8HkkcdzwoBAgcdVJf2fDmx13HT8vm/SHtuvGTvIzBggUOS2/MSLQ/8veqqqdHun1AIjF3goenAXvt7H88/ZOyQ8ifQSOBnU08fx9z2Nv4gbdanpgoBAgMXqI9gnp7YfgB3/Xt91PSwgbtIj8CBBA7Pkx9MdH2s7FX/u5ND/eGqEJi7QF83V9p+TP5W0F3GMPc9T/9HJ/CUZLz9QO769/rI6TGjU5IwgYsEHp4fXR8ji9Tv0xJ75NwFasD5uxs4Hp88d3j9JzBmgccn+UVeZFsu86Qxg8l9lgKXTK9rur2Wx8EqdZ2cHHyUOstdUKf3CdSnG89PrHL8rLPOY22BaQt4237a23erdz+WX+qObH1u76elvZ9M1AlImZ/AndLlR4+o20cn1yHMOPLO5FFfmptjqTtZvXGOHdfn/xGoy4pekLjv/zzS/S/1yeSPJp7dfVNaIECgD4HvSyN9T+nyh2nTtYh9bN3htfGgpLTOuy3WnZ9fzbGqzFeg7ij4ikSfx/4Fae+750uu5wSmK1B/Nfc9afcL02b91a7MS8CAt98X7j4HCV21ZcA7r3PE9t7WbXtfl+hq39qp3i+kve/YnoTfpy3gWrFpb9/9e/fiPFAHeM2d21epF7GXJOqvd4UAAQIECGwXuHL+8y+Jugyqr/LZNHSvxEv7alA7mxcw4N38Nug7g/rI6B6Jc3tsuNqrdo/qsU1NESBAgMCwBY5Jeq9J3LrHNM9OW9+ceGWPbWpqAAIGvAPYCBtIoT46ulvirB7brr/eX5W4So9taooAAQIEhilwnaRVr0U36TG9T6StuyZ8ObJH9KE0ZcA7lC3Rfx4npclvSJzRY9P1V/xrE9fosU1NESBAgMCwBG6UdGqwe3yPadW0g3dJ1NR/ygwFDHhnuNG3dbmmQKqpmE7d9ljXv9aJ7vWJ63bdkPoJECBAYHACt0pGfb/x8YG0Wa91c53yb3A7wSYSMuDdhPqw2qwTQV1u0OeJ4Li0V4PemyUUAgQIEJiHwB3Tzb4vbdvEGzvz2Joj66UB78g2WEfp/lfq7fujnqulzfqywu066pNqCRAgQGA4At+UVP4xUVOQ9VU2celeX33TzpICBrxLgk148a2L+d/QYx+vmLZemTixxzY1RYAAAQL9Ctw7zf1d4jI9NruJL2f32D1NLStgwLus2LSXr+laviVRg9C+ypFp6O8T395Xg9ohQIAAgd4EvictvShxRG8tXjQNZt/Tb/bYPU2tImDAu4ratNfZxITclwxp3RTjwdOm1TsCBAjMSuDh6e3zE4f22OtN3GCpx+5pigCB1gJ1gvqzxE63ZOzqsS+lvTpBKuMXeFC60NV+ot5p2rq18PiP++09eOwGzgF/nDYP2Z6E3wkQILCIQH0C8KxE3wOMxy2SnGUGLWDA2/9x0/dx2ro9A95BH9JLJfdLWbr1/rFXfc9MmwcvlaWFCRAgsJ/A/83/9zrZtH7+Kfvl4L/jEjDg7f+YaX0M9l2fAe+4jvGdsq0B59MSfe87v7JTMh4jQIDAKgJPzEp9n8SekTb9xb7K1tr8Oga8/R8vfR+frdsz4N38cbtOBvWJ4HMTrfeLver7mXWSti4BAgR2Enh0Htzr5NP6+b6/8LBTvz22vIABb//HSutjr+/6DHiXP86GssZhSeQvE33uM19Oe/97KADyIEBgegI/lC7Vl8v6PLH9v7TX55Q209tq/ffIgLffY6TP47Grtgx4+z9OW7RYs+y8LNHVfrFTvRemvYe2SF4dBAgQOJDAA/Pk+YmdTkRdPfZPae9SB0rKc4MSMODt9/jo6rjrs14D3kEdwgslU/Oo/0uiz/3ki2nvfgtlZyEC2wTqmhuFwLIC9dHVdya+sOyKayxft6X8u0S9m6AQIECAwGYF6q5pddOgu/aYxufTVt217a97bFNTExEw4J3IhtxAN+ojrG9NfKbHtu+Wtl6Y6HMS8x67pykCBAiMQqCu2a0bPNypx2zPTVt197R/6LFNTU1IwIB3QhtzA115Vdqsd14/3WPb35a2nt5je5oiQIAAga8VqPnZ6zb0fZWz0tA3Jl7bV4PamZ6AAe/0tmnfPXpTGjwx8bEeG35E2vrRHtvTFAECBAhcJFCz9fxAjxhnpK1vSLylxzY1NUEBA94JbtQNdOltafMuiY/02HZNbn7bHtvTFAECBOYucMcAPLVHhNPS1p0T7+yxTU1NVMCAd6IbdgPdel/arOu53t9T24ennT9P1BcnFAIECBDoVuCoVF/n3L6+Q/HetFWvKR9IKATWFjDgXZtQBdsEPpzf66/xt297rMtfr5/K3VKyS2F1EyBA4CKBemf32J4wTk479anhR3tqTzMzEDDgncFG7rmLZ6a9ExNv7qndR6ad2/XUlmYIECAwR4F6p/WHe+r4v6Wdmurs4z21p5mZCBjwzmRD99zNT6W9+kbta3pot/bhmrXh4B7a0gQBAgTmJlDn2Gck+jjH1k0svjlxdkIh0FTAgLcpp8q2CZyX3++ZqInJuy71Dm/d/U0hQIAAgbYC35fqbtm2yh1r+9s82vfc7jsm4sFpCvTxF9s05fRqUYGaoLy+6PBdi66w4nL1pbkbJ7684vpWaytwrVR3+7ZVHrC2I/LscxP1c5OlZir5yU0mMOK266Ns12wOawPWF9T+M3Fcx2n9Rep/SOLCjttRPQECBDoVOCS1/2Gi6/utP6DTXqh8yAJ1LXfX+9ci9T9syEhyI7CkQL27u8h+v84yz04bPm1ecsNYnACB4QrUpwm/nVjnxLjXuvUOkTI/gUuly6cn9to/un7+3cmhrymb5reV9XgTAjVbQpfHzW9solPaJECAQB8Cv5xGujyB3rqPTmhjUAJ1CUGX+9SidXd92c6g0CUzeYG6ycSi+/4qy/3C5AV1kACB2Qs8OQKrnCAXWae+TazMR+DIdPUTiUX2jS6XOSk5+Fh2PvvdHHr6Bx0eVz87B0B9JECAQAl0dTKtuRt9rDyffaxeOLscyC5a993nQ66nMxA4PH38dGLR/X+Z5Z45Az9dJECAwP8I1Am13hVb5kS56LIn/k8rfpmywOXTua5elBfd12q5VyfMeBMEZTIC90hPljkGFl32janXGxKT2U10hACBRQVukgW/mFj0ZLnock9dNAHLjVqgy0tjFt3Xarm61lEhMCWBupnPMsfAIst+PnXeYEpI+kKAAIFlBH49Cy9yslxmmbcuk4BlRylw5WR9bmKZ/aKLZWuyfIXA1ATekw61Pl5+aWpI+kOAAIFlBK6YhVsPXL6UOi+7TBKWHZ3AryXj1i/Iy9ZXNzm5xejkJEzgwAJXydPLHgt7LV+XHh114GY9S4AAgekLdDE/74nTZ5ttD6+Wnn8usdeLbNfP/9lst4COT1mgbgnf+tipP1AVAgQIzF7g5hFofYL9idmrThfgaR3sL8vufxckh+tNl1jPZizw+PR92eNhr+VduzvjHUrXCRD4WoHW14z97tdW738TEbhW+tHFFx33esHe//nfn4inbhDYX+B5eWD//X2d/79t/wb8n8AmBEyUvgl1be4k8I87PbjGY9dZY12rDlfg55JaTWm3yfKFNO4LOJvcAtruUqD1ubP1ub3Lvqt7wgIGvKPAj5IAAChqSURBVBPeuCPr2psa53uNxvWpbvMCxyeFH9x8GgfVlE3/NYA8pECgC4HW587W5/Yu+qxOAgQI9CZwq7S0zsdm+697Rm+Za6gvgT9qvI/sv88s8v9zksOV+uqwdghsQKD1zVxuuoE+aJIAAQKDFah5VRcZcCy6zGcG21OJrSJww6xU080tuv27Wu4JqyRvHQIjEmh9nJmObEQbX6oECHQvcFiaaDlIqW/RK9MReEG60nL/WKWujycH8ztPZ5/Sk4sL1PXxqxwbu61Tc1UrBAgQILBN4JD8vttJc5XHL9xWt1/HLdDFtHWr7FOmuhv3fiT7vQVaD3idh/c2twQBAjMTqHfOVhmE7LZO3bddmYbAi9ON3bZzX49/ODkcMQ1OvSCwq8DBeabelW15XG16VpVdO+sJAgQIbELg+mm05Un2E5vohDabC9ym8X6x6j72sOY9UyGBYQqcl7RWPU52Wu/aw+ymrOYmYFqyuW3x4fa39V2rzhpuV2W2hMAQ5rutm6I8f4mcLUpgzAKfapz8DRrXpzoCKwkY8K7EZqUOBG7ZuM4zG9enuv4F7pgm79l/sxdrsWZmcC3ixVg8MFGB1lM63mKiTro1MgED3pFtsAmne0Ljvp3WuD7V9S8whHd3T0q3/7r/rmuRwMYETm3ccutze+P0VDcXAQPeuWzp4fez9UnxfcPvsgwPIHC3PFex6VK3Mq7rEhUCcxFofe5sfW6fy3bQTwIEJihw6fSp9WTn95mg01y6VN8U/9fETl+A6fOxVyeHykUhMCeB+6ezLY+z81OfGU7mtAfpKwECuwrcIc+0PMFWXdfZtTVPDF3gHkmw9f6wSn1fP3Qo+RHoQKD1jDl17N26gzxVSYAAgdEJPCIZrzIg2W2ds0cnIOEtgXpH9S2J3bZtX4+/dCshPwnMTKCOwXMTLY+1H5iZoe4OUMA1vAPcKDNMqfUMDafM0HAqXb53OlJz726y1Av9z28yAW0T2KBA7f+tz6Gu493gBtX0RQIGvPaEIQi0PhmePIROyWFpgTofDWFmhhckj7ctnb0VCExHoPU5tPU5fjrSekKAwGwEapDzmUTLj88eNhu9aXX0gY33g1X2qQuSw3Wnxao3BJYWqHPoKsfPbuucvXQGViBAgMDEBG6Y/ux2klz1cV+QGN9OcmhSrjuarbrNW633e+OjkzGB5gK3So2tjqmtenyRuPlmUuEyAvUioxDYpEDrj7rqHbp3brJD2l5J4KpZ61mJuqNZTVFXsfX7bj+7WObLaVchMHeBOofWufSwhhB1rv9Qw/pURYAAgVEJ/Eqy3XoHoMVP116OavNLlgCBgQqcnLxanJO36njyQPsprZkI1PWTCoFNCrR+h7dO0goBAgQIrCfwH+utfrG1W8/Gc7EGPEDgQAIGvAfS8VwfAga8fShrgwABAssJtB7wtj7XL9cbS89ewIB39rvARgHqus2rNc7AO7yNQVVHgMAsBVoPeI+N4uVnKanTgxAw4B3EZphtEl38xd96wvTZbhwdJ0Bg1gJ1Lq3rb1uWLs75LfNT14QFDHgnvHFH0LXWJ7+Pps9njaDfUiRAgMDQBer2wh9snGTrc37j9FQ3ZQED3ilv3eH3rfXJ7+Thd1mGBAgQGI1A68saWp/zRwMp0c0LGPBufhvMOYPWJz8D3jnvTfpOgEBrAQPe1qLq25iAAe/G6Gff8KUicP3GCga8jUFVR4DArAVan1NvHM2WN7OY9cbR+eUEDHiX87J0O4Gbp6pD2lX33zW1Pjk3Tk91BAgQGJVA63d4D0/vbzIqAclORsCAdzKbcnQdOaFxxuelvtZfsGicouoIECAwKoEzku3HGmfc+tzfOD3VTVXAgHeqW3b4/Wp90qtbCreeQmf4ijIkQIBAtwKt3+Vtfe7vtvdqn4yAAe9kNuXoOtL6pHfy6AQkTIAAgeELGPAOfxvJcAEBA94FkCzSXKD2u7qGt2Ux4G2pqS4CBAhcJND63HpLsAQ2IWDAuwl1bV4vBEc2Zmh9Um6cnuoIECAwSoHW7/BeIQp1m2GFQK8CBry9cmtsn8AJjSUuTH3vaFyn6ggQIEDgoIPeH4T6UnDL0vo1oGVu6pqogAHvRDfswLvV+mT33vT3CwPvs/QIECAwRoH6MvApjRN3WUNjUNXtLWDAu7eRJdoLtB7wntw+RTUSIECAwD6B1ufY1q8BNhSBPQUMePckskAHAq1Pdq1Pxh10WZUECBAYrUDr63hbvwaMFlbi/QkY8PZnraWLBI7Oj6s3xmj9cVvj9FRHgACBUQu0HvAeF43LjVpE8qMTMOAd3SYbfcJd/GXvHd7R7xY6QIDAgAXemdwuaJjfwanLdbwNQVW1t4AB795Glmgr0Pokd3rS+0TbFNVGgAABAtsEzs/v79r2/xa/dvHmR4u81DFRAQPeiW7YAXer9UnOu7sD3thSI0BgMgKtL2to/VowGWgd6UbAgLcbV7XuLtD6JGfAu7u1ZwgQINBKoPWAt/Wnfa36qZ6JChjwTnTDDrRbl0xeN2ycmwFvY1DVESBAYAeB1gPem6aNQ3dox0MECBAYvcDXpQc1iXnLuP7oVXSAAAECwxc4Kil+OdHy/H3z4XdbhlMR8A7vVLbkOPrR+nKGz6TbHxhH12VJgACBUQucm+w/2LgHrV8TGqenuikJGPBOaWsOvy+tT25vT5frHQeFAAECBLoXaH1ZQ+vXhO4FtDBaAQPe0W66USbe+uR28igVJE2AAIFxChjwjnO7yToCBrx2g74EaqLxWzRuzIC3MajqCBAgcACB1udcMzUcANtTBAiMU6C+XNbyyw5V1+3GSSFrAgQIjFKgbgvf+jx+zVFKSHp0At7hHd0mG23CrS9n+FIk6hpehQABAgT6ETgjzXyscVOtXxsap6e6qQgY8E5lSw6/H61Pau9Llz8//G7LkAABApMScB3vpDbnfDpjwDufbb3pnrYe8J6y6Q5pnwABAjMUOLlxn1u/NjROT3VTETDgncqWHH4/Wn85ofVJd/iCMiRAgMDmBbzDu/ltIAMCBAYqcOXk1fqLDncfaF+lRYAAgSkLtP4Ccs2lftkpg+nbMAS8wzuM7TD1LLr4yKr1uwxT3wb6R4AAgRYC708l57WoaF8dNWVl608AG6anqqkIGPBOZUsOux+tB7xnprsfH3aXZUeAAIFJCtSndW9r3LPWrxGN01PdFAQMeKewFYffh9Yns5OH32UZEiBAYLICrT9h8w7vZHeV4XTMgHc422LKmRjwTnnr6hsBAnMTaD3gbf0aMbftob8LCBjwLoBkkbUELpm1b7hWDRdf2Tu8FzfxCAECBPoSaD3gvVkSP6Sv5LVDgACBLgRum0pbz9Bwoy4SVScBAgQILCRweJY6P9Hy3H7ThVq2EIEVBbzDuyKc1RYWaP1R1efSct1lTSFAgACBzQjUYPddjZtu/VrROD3VjV3AgHfsW3D4+bf+MsLb0+Wat1EhQIAAgc0JtL6sofVrxeZktDxIAQPeQW6WSSXV+mMq1+9OavfQGQIERirQesDb+rVipKzS7krAgLcrWfVuCRy39Uujnwa8jSBVQ4AAgTUEWg94j10jF6sS2FPAgHdPIgusKXClNdfff3UD3v1F/J8AAQL9C5ySJutLa61K69eKVnmpZyICh06kH7oxXIH6Nm/Lcr9UduPEqfviI/l5YUIhQIAAgW4EanrJ4xLX2S++lP+3Gke0fq1IagqBrwrUPawVAl0KnJ3KL9dhA3XC/Wji1H3xoW2/12P1XC2jECBAgMDOAjUH7rUS+w9ot/5/tTzX9XjhjLRxTEIh0IlA1ztwJ0mrdFQC70+2191gxhek7a0B8f6D4fr/6QmzPmxwA2maAIFeBK6aVrYGsMdv+70eq8Fuq3dqU9VKpWbgucVKa1qJwAICm97BF0jRIiMX+EDy3+SA97C0v3WSv+sOljWfZF0WcWpi+4B46/d61+ErCYUAAQJDFqhP0rbOdfv/PC7PXXrIySe3Dw48P+mNXMCAd+QbcATp15fMvmXAedZ1YzUg321Q/sU89+HE1gD41P1+PzP/VwgQINC1wBFpYP+B7Pb/X6HrBDquv74EpxDoTODgzmpWMYGLBL49P146YYzPp2+nJU7dF9sHxvXYxxMKAQIE9hI4JAtcM7F9ELv996vnuSm/Zn9z+vfPCYVAJwJTPng6AVPp0gL1MdonE5daes1prPDZdOO0xKn7YvuAuH4/K6EQIDAPge3X0W4fzNbvdR1tXYI1x3JuOn2VRF1iphDoRMAlDZ2wqnSbwOfy+0sSD9r22Jx+vUw6e5N9sVO/z8uDWwPiuobtfYl3JGpS93oRUAgQGJdAXUt7q8TNEtdPbH1B7Lj8XucD5eICL8pDBrsXd/FIQ4GDG9alKgK7CdwpT7xutyc9vqPAV/LoOxOvSrwi8crEFxIKAQLDEqhPr74pcffEXRM1T7jX1iAsUb4uy75lieUtSoAAgcEKvDaZ1SBOrGZQ7wT/WaJeVC+RUAgQ2JxAXW/7rYm/TNRlS85rqxvUH/QKAQIEJiNwu/TkSwkvDOsb1KUPP5W4bEIhQKA/gcunqZ9O1GVIzmXrG1wYx1smFAIECExK4LfTGy8S7Qw+Fc8nJI6c1F6iMwSGJ3BUUvrFxDkJ57B2Bk8d3qaWEQECBNYXqPux17y8XjDaGpwR0x9IuG4wCAqBhgJ1+dDDEzW9oPNWW4M3x/SIhEKAAIFJChybXtUAzYtHe4P6YuANJ7nX6BSB/gVumib/LeFc1d7gI3G9Rv+bVIsECBDoV6Cm6/lYwgtJe4OaBu7H+t2cWiMwOYFHp0c1K4pzVHuD0+PqD/PJHTI6RIDAbgLXyxPvTXhB6cbghbF1be9ue5/HCewsUHPo1rzhzkvdGLwrttfZmd6jBAgQmK5Avbj8RcKLSzcGb4/tsdPdffSMQFOB66a29yScj7ox+NPYmlmm6S6rMgIExiZwnyRcU215oWlvUB8f3mJsO4R8CfQscJu054tp7c8/dU5/f+I7et6emiNAgMBgBeoe8j+YOCVh4NvWoKYvqxd0hQCBiwvcMQ+ZbqztOafO4XUuf1ji0IRCYOMCpjHa+CaQwA4CNRH5vRMnJmqgVnNgKusJfDqrn5h423rVWJvApARum97UbbudY9bfrJ9JFSclXpWo66BrCkqFwGAEDHgHsykkcgCBq+e5+qLD/nF8Hrtm4pCEsrfAmVnkDonT9l7UEgQmL1BfnH1D4iqT72mbDn451fxX4kO7RD1X7+wqBAYpYMA7yM0iqSUE6uOyaye2D4ZrILz1/6OXqGsOi74znfz6xHlz6Kw+EthF4PJ5vObYNT3W1wJ9Mv/dbUBbfyif/7WL+x+B8QgY8I5nW8l0NYHLZLXjElsD4Pq5fUA8x28NvzgG90soBOYoUK97f5f41hl2vi472G1AW4/X8wqBSQrUga8QmLPAldL53QbDx+a5wyeK8+Pp19Mn2jfdInAggcflyV870AIjfu6C5H5aYqdBbc2EU+/gKgRmKWDAO8vNrtMLClwiyx2T2G1AXM/VMmMsdRepWyfePcbk5UxgRYH6QuybEzUrzBhLXUdbUw3uNKCtx+o62lpGIUBgPwED3v1A/JfAEgL17m+9C7w1IN5+qUQ9Vu8eD7m8KcnVlExeIIe8leTWSqC+3Fr7/G1aVdhRPWel3q0Bbb0ru/V7/Twt4TraICgElhUw4F1WzPIEFheo64N3GwzX45devKrOlnxEan5WZ7WrmMBwBB6VVH5nAOl8NjlsH8Tu//t5A8hRCgQmJ2DAO7lNqkMjEqgZJOpd4esnbpU4cd/P/Oit1DV9NT1TTbyvEJiqwBXTsbrj1xV67OBX0tZbE69O/EfiPxM1uP1EQiFAgAABArMWuHZ6/zOJDyfqBbOP+D9pRyEwZYFfT+f6OJaqjQ8l6otx10goBAgQIECAwAEE6ks1P5Kom0V0/UJdH6EO/XrjpKgQWEngylmrLiPo+jiqL4w9LOFGOEFQCBAgQIDAMgKXy8J/mOj6xfrJyyRlWQIjEvjl5Nr18fPstDHHOb1HtBtIlQABAgTGIPC9SfLzia5euD+Vuo8cA4QcCSwhUIPQTye6Om7qneMHLpGPRQkQIECAAIE9BO6c589NdPXi/VN7tO9pAmMTeGwS7up4qYF03aZbIUCAAAECBBoL3Cn1fS7RxYt4XYNYcwsrBKYgUPty7dNdHCt1C97bTwFJHwgQIECAwFAF6iPULl7Eq84fHmqn5UVgSYHal7s4TupGLd+5ZC4WJ0CAAAECBFYQ+N2s08WLec0V6lvmK2wQqwxK4BLJ5n2JLo6R3xxUTyVDgAABAgQmLHCZ9O20RBcv6A+asJuuzUPg/h0dGx9IvZeaB6FeEiBAgACBYQg8OGl0MeA9eRjdkwWBlQVOyppdHBv3WzkjKxIgQIAAAQIrCdStwd+Z6OKF/VtXyshKBDYv8C1JoYtj4pTUW8ecQoAAAQIECPQs8JC018WL++t67ofmCLQS+JdU1MUx4VKfVltIPQQIECBAYEmBQ7P8hxJdvMDXFGgKgTEJ3C7JdnEsvD/1+jLnmPYEuRIgQIDA5AQemR518SL/sslJ6dDUBV7c0bHwI1OH0z8CBAgQIDB0gUsmwTMTXQx6bzn0zsuPwD6BG+VnzZHb+jiom1ccsa8NPwgQIECAAIENCjw+bbd+oa/6/mKDfdI0gWUE/igLd3EMuOX2MlvBsgQIECBAoEOBo1L32YnWL/gXps7rdZi3qgm0ELhmKjk/0Xr/Pyt1HtkiQXUQILBZgbobjUKAwPgFzk0X6u5rrUt9UedxrStVH4HGAvUu7GGN66zqnpH4TAf1qpIAAQIECBBYUeDorPe5ROt3ub6YOo9ZMSerEeha4EppoAalrff7qrPqVggQmICAd3gnsBF1gcA+gY/n53M70Dg8df5kB/WqkkALgUelkrrVduvy7FRYlzQoBAhMQMBdYyawEXWBwDaBY/N7zRla8/O2LPVuV9X9qZaVzqCumkGj3Ood8isn6nrQ+gOiSl1zel7ik4nTEx9OfCGhLC5QA93TEq3fia1tc3yiZmhQCBAgQIAAgQEK/HFyav3xbtX3xAH2dUgp1eD2rvucXpqfpyaWmSarlv1Q4iWJn0+cmKg6ld0FHp2nutjX/2D3Jj1DgAABAgQIDEHgxklimYHWogOGeieyi4+Oh2C2ag71rm3dlODvE59PLGq56HJ1TXbdAOQHE1dMKF8VqC+pfSSxqOWiy30pdV7/q834jQABAgQIEBiqQFd3nHrMUDvcY151Kdi3JMq4PvpedCC17nL15cEXJr4xoRx00A8EYV3Tndb/S7gECBAgQIDAOAS+Lmnu9GK+7mMfTb1b16COQ6JdljVF20MS70is67ju+m9LDt+dmOsXj6vf7+5oO5yQehUCBAgQIEBgJAL/nDzXHVjttH59vD638p3p8HsSO3ls8rF3Jqd7z21jpL/37Whb1KUpCgECBAgQIDAigbsl1y4GY+9NvXN5Z/EO6evrOnJsuW1emxxvn5hLeVM62tJvq647zwVQPwkQIECAwJQEuhoY3H9KSDv05bp57K8SWwOhsfx8UXKe+q2gu/pD7vU77AceIkCAAAECBEYgcJ/k2MVg7a0j6PsqKdZ8rk9L1BfEunDro876It0zEldJTLH8YzrVheO9poilTwQIECBAYA4CNaNAXefZxQDhHhMCrPluH5c4uyOrLvz3qvPc9KXm8710YirlNunIXv1e5fmTpwKkHwQIECBAYK4CNbPAKoOAvdZ5zQRA6w+C8jmtI6O9DPt4vu4W9kOJmmVi7KWmZevC7EFjh5E/AQIECBCYu8ChAfhQoouBwh1HjFvXgp7UkUsX1uvWWdOpfduIt1fdDOJLHWyv96fOKfwxMOJNK3UCBAgQINBG4JGpZt0B007r/22b9Hqt5aZp7WUdeexkNLTHXpW+37ZX8TaNPaejbVZ3ylMIECBAgACBCQjUNapnJloPvuoWxjcfic/Vk2cNmi5MtHYYW3213f4icXxiDOWYJNnFFwnrco8jxgAgRwIECBAgQGAxgcdnsS4GZn+2WPMbW+rItPzkxGcSXfR/zHXWILJmpajZKYZc/m+S68L5p4bcabkRIECAAAECywsclVW6mIWg3jEd4juFdV3mIxJdvLPdxeBrk3XWflF/EF0yMbRyhSRUM0609jkrddYfQwoBAgQIECAwMYGnpD+tBw5V3+8PzOnbk8+7OuprF35DqfPDMfv+xCUSQyk1tVoXPvWuv0KAAAECBAhMUODo9OlzidYDiC+kzrpGdtOlvoz16kTr/s2tvlNieI/EpkvNIfyJRGv/urxl6JdxbNpe+wQIECBAYNQCT0/2rQcQVd+vb1DluLT954n6MlYXfZtrnf8Uz1slNlUelYa7sP/NTXVIuwQIECBAgEA/AsemmQsSrQcSdZ1lXW/ZZ6n26gtN9Q5z6/6o7yLT+iOivphY+02fpeaPPjXRejvUF/WukVAIEJiRgMm2Z7SxdZXAPoFz8vN6iVs2Fqnpneqj4tc2rnen6qqtRydelLhbogZHQy41/dVJiTfui/r9vYlPJqovl00MtdTd6G6e+NFE/YHx5kT9gdF1+Z408AMdNPK81Dn0mUU66LYqCRAgQIDA/ARunC538fF/XW9Z1112VWrw9eDEhxKt3/lrWV8NCGswXoO2Ra5trncc6xbHL07UO5Atc2ld16eS32MTNVDvqtR2fkeide51p7brd5W0egkQIECAAIHhCdTgqvWAour7iY66epfU++8d5dzK4dPJ7wmJKydWLVfJik9KdDGFXKt+Vj2nJmqQXoPT1uU7UmHLXLfq+svWiaqPAAECBAgQGLbA1yW9rYFAy581tdVhDbt+o9T1ko5ybdXvekf3NxJXTLQqNYvA0xJDf8f3rcnxm1p1el89b8jPVttmez0nNM5TdQQIECBAgMAIBP45OW4fELT6vcW1l1dNbr+XuKCjHFv0desLXcclx67K8an4BYkuLkFpYbBVxyuS4y0aINQ7+Vt1tvz59w1yUwUBAgQIECAwQoH6wlfLQcVWXe9JvZdY0aOuAX5i4rzEVn1D/PnK5HfrRF/ltmnoVYkhWmzlVNfI/nHiWolVSw1Mt+pr+fPOqyZkPQIECBAgQGD8Am9KF1oOLLbqut+SNDVrzA8lTu8on6281v35tuR3z8Smyrel4S6+0LWuy/b1P58cfy1xuSWRauaQ7fW0+v31S+ZhcQIECBAgQGBiAvdJf1oNLLbX85YlnGoA+faO8tie0zq/fyT5fX9i1Xeus2qzUn8c/GCipjtbp09dr1vTrj0mcXhikVKXbnSR070WadwyBAgQIECAwHQF6lv270x0MdD45j3YbpXnu7qOuFV/araExycutUdfNvF0Xf7xc4lzEq3620U9H0x+D04caEaH6+b5Czvox8mpUyFAgAABAgQI/Pf0Ul0MdF61i+218/jzE19OdNFuizprdoSnJWq2hKGXmsrs6YnzEy363lUdddOKuyZ2Kr+fB7to90E7NeYxAgQIECBAYH4Ch6bLH0p0MeC4wzbOuqazru2sazy7aKtFnTUI/4vE8Ymxlesl4RcmWjh0WcfLk+PNtuFeLb9/oYO835866/IPhQABAgQIECDw3wKPzL9dDHJqDt2al/cnEnVNZxdttKrzVcmv5icee6k/Ml6baOXSRT01o8NzE3WXuV/tKNcfSb0KAQIECBAgQOB/BC6Z385MtB7c1DumH+yg3pZ51qwH35aYWrl3OvTuREur1nV9Lvl9toMc6wt9Xd7+ONUrBAgQIECAwBgFHp+kWw9ohlxfDYpqtoMpf+xdfXt44ozEkLdF69x+Kv1VCBAgQIAAAQIXEzgqj9SsBK0HH0Orr2Y1qNkNapaDuZTLpKO/kDgvMbTt0Tqfs9LHIxMKAQIECBAgQGBHgafk0dYDkKHUV7MY1GwGNavBXMtV0/HfSwz5ls3r7i9PnuvG1W8CBAgQIEBgMYGjs1hdV7nuoGNo69fsBTWLgXKRwA3z4/8lhrad1s3nM+nTlS7qon8JECBAgAABArsL1Lug6w48hrJ+zVZw+927Ovtn/lcE3pAYyvZaN4/fnP0WBUCAAAECBAgsJHBslhr7R941O0HNUqAsJnC/LPa+xLoDzk2uXzcLucZi3bUUAQIECBAgQOCgg/44CJscvKzads1GUPOvTnnmha72z7oByY8lPpZY1X+T6/1BVzDqJUCAAAECBKYpcON0a8i3/t1/YHVe8n1iomYjUNYTuGxW/8VEXQ+7v/NQ/183srh+QiFAgAABAgQILCXwV1l6qAOcrbzq0ovfTdSX7ZS2AldPdc9OXJjY8h7qzz9t23W1ESBAgAABAnMRqFkN6rrIoQ5yXpzcbjCXjbHBfta7/S9NDHU/qFlFjt2gj6YJECBAgACBkQv8fPIf2kDnX5PTHUfuOsb075Kk35QY2v7w2DFiypkAAQIECBAYjkB9+evViSEMct6bPO6bUDYr8IA0//7EEPaJVySPS2yWQ+sECBAgQIDAFATqzmQfSGxqgHNm2v7RRM0ioAxD4LCk8eOJTyQ2tV/UH0BXTCgECBAgQIAAgSYC10ktpyX6HNzULAF1m9gjE8owBY5KWk9J1HW0fe4b9Q7ztRIKAQIECBAgQKCpwDVT238kuh7YXJg2npW4WkIZh0Dd8OEPEzU9WNf7x7+nDftGEBQCBAgQIECgG4FLp9rnJLoa1Lwkdd+om9TV2oPAzdLGyxNd7R/PTN1H9NAPTRAgQIAAAQIEDvrmGLwz0Wpg88bUdWeukxG4a3ry5kSr/eNtqavqVAgQIECAAAECvQrUDA4PTqw6VVXdye2ViXsllOkJHJwu3TvxmsSqA983ZN37J8zEEASFAAECBAgQ2KxA3ZzgZxL/lPhUYrcBTn2rvz7y/snEcQllHgLHp5s1X+4/JD6Z2G3/OCvPvSLx04kbJhQCBAisLVB/fSsECBDoQuDoVHr1xGX3VX5Ofp6eqAGNQuDKITgmUbM8VDk3cUai/iBSCBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIEZiXw/wPxpudNEypX+wAAAABJRU5ErkJggg=="
                    return HttpResponse(base64.b64decode(image_base64), content_type='image/png')
                else:
                    #Same file path exists in the previous version. New version of file has same md5. Show blank icon.
                    image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAApJREFUCNdjYAAAAAIAAeIhvDMAAAAASUVORK5CYII="
                    return HttpResponse(base64.b64decode(image_base64), content_type='image/png')
            except m.GitFile.DoesNotExist:
                #File path does not exist in previous version.
                image_base64 = "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Man/LLf7fC4Y2kUAAQQQQACBdgrsoGGV/NW/CydW1yrfdyl8NQLKdAKra/P3KrwedqFzqf/3F1lso6AggAACCCCAAAKVBP5TtUud4PTy8tKLTyn8YTtKrMBGau6zitsUPe9Sb78aO3RaQwABBBBAAIGuCPiqBl4XWeok53Dltm1XdsYMx+mz/d9VlPo88FVFNp+hD10jgAACCCCAQMMF3qH8S5vo/K9yenjDXZuY/t5K+jhFac+HNzURk5wRQAABBBBAoBwBf/hrTlHCJOdM5fEMBWW2As9S92crSnhO/Fh53Ge2HPSOAAIIIIAAAm0Q8DeTnaOY1QTnYvX9KoWvIkApQ2B5pfE6xZ8Vs3pe+A+gtRUUBBBAAAEEEEAgRGALtXKeos7Jja8S4K+JXU1BKVNgDaX1foXX0db53PAZ5vspKAgggAACCCCAQKjApmrt94rcE5vb1MdnFBsqKM0Q8Bc+HKrw5cFyPz9+rT54bgiBggACCCCAAAJ5BFZRs59T5JrUfEdtb58ndVqtQWAn9fEDRa7nxyfV9oo1jIMuEEAAAQQQQACBRY+WwamKqInNL9XWXri2RmA/jeQ3iqjnx0lqy21SEEAAAQQQQACBWgV8BYfnKia9VJW/ye3niicqKO0TWEZDeqriSMWkE99jte0zFVyJQQgUBBBAAAEEEJitgL+c4G2KnyquUAyb4PhT/X7L++8UixWUbghsqWH6erk/UlymGPb8uFyP/VjxFsV2CgoCCCAwtYD/+qYggAACOQTWV6MbKVafb/xq3V6o8ISGgsC6IthY4as8uFyjuEjhP4goCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIDA/2+HDgQAAAAABPlbD3IhZMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYGA1EKmtYlvt42i0AAAAAElFTkSuQmCC"
                return HttpResponse(base64.b64decode(image_base64), content_type='image/png')
        else:
            #There is no previous version, so file path is new
            image_base64 = "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Man/LLf7fC4Y2kUAAQQQQACBdgrsoGGV/NW/CydW1yrfdyl8NQLKdAKra/P3KrwedqFzqf/3F1lso6AggAACCCCAAAKVBP5TtUud4PTy8tKLTyn8YTtKrMBGau6zitsUPe9Sb78aO3RaQwABBBBAAIGuCPiqBl4XWeok53Dltm1XdsYMx+mz/d9VlPo88FVFNp+hD10jgAACCCCAQMMF3qH8S5vo/K9yenjDXZuY/t5K+jhFac+HNzURk5wRQAABBBBAoBwBf/hrTlHCJOdM5fEMBWW2As9S92crSnhO/Fh53Ge2HPSOAAIIIIAAAm0Q8DeTnaOY1QTnYvX9KoWvIkApQ2B5pfE6xZ8Vs3pe+A+gtRUUBBBAAAEEEEAgRGALtXKeos7Jja8S4K+JXU1BKVNgDaX1foXX0db53PAZ5vspKAgggAACCCCAQKjApmrt94rcE5vb1MdnFBsqKM0Q8Bc+HKrw5cFyPz9+rT54bgiBggACCCCAAAJ5BFZRs59T5JrUfEdtb58ndVqtQWAn9fEDRa7nxyfV9oo1jIMuEEAAAQQQQACBRY+WwamKqInNL9XWXri2RmA/jeQ3iqjnx0lqy21SEEAAAQQQQACBWgV8BYfnKia9VJW/ye3niicqKO0TWEZDeqriSMWkE99jte0zFVyJQQgUBBBAAAEEEJitgL+c4G2KnyquUAyb4PhT/X7L++8UixWUbghsqWH6erk/UlymGPb8uFyP/VjxFsV2CgoCCCAwtYD/+qYggAACOQTWV6MbKVafb/xq3V6o8ISGgsC6IthY4as8uFyjuEjhP4goCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIAAAggggAACCCCAAAIIIIDA/2+HDgQAAAAABPlbD3IhZMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYMCAAQMGDBgwYGA1EKmtYlvt42i0AAAAAElFTkSuQmCC"
            return HttpResponse(base64.b64decode(image_base64), content_type='image/png')
            #return image is new

#This gets the list of files from the running container and compares it to our local list. The differences are presented to the author to approve.
class SubmissionReconcileFilesView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GitFilesMixin, GenericCorereObjectView):
    #TODO: Maybe don't need some of these, after creating uploader
    # form = f.SubmissionUploadFilesForm
    # template = 'main/form_upload_files.html'
    transition_method_name = 'edit_noop'
    page_help_text = _("submission_reconcileFiles_helpText")
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission

    def dispatch(self, request, *args, **kwargs):
        self.page_title = _("submission_reconcileFiles_pageTitle").format(submission_version=self.object.version_id)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        #here we need to get the list of files from WT, compare them to our files_dict_list, and return back the differences.
        #... or well maybe the info about the differences can be done with SubmissionFilesCheckNewness (probably will require expanding that method)

        pass

    def post(self, request, *args, **kwargs):
        pass

#NOTE: This is unused and disabled in URLs. Probably should delete.
#Does not use TransitionPermissionMixin as it does the check internally. Maybe should switch
# class SubmissionProgressView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericCorereObjectView):
#     parent_reference_name = 'manuscript'
#     parent_id_name = "manuscript_id"
#     parent_model = m.Manuscript
#     object_friendly_name = 'submission'
#     model = m.Submission
#     note_formset = f.NoteSubmissionFormset
#     note_helper = f.NoteFormSetHelper()
#     http_method_names = ['post']

#     def post(self, request, *args, **kwargs):
#         try:
#             if not fsm_check_transition_perm(self.object.submit, request.user): 
#                 logger.debug("PermissionDenied")
#                 raise Http404()
#             try:
#                 self.object.submit(request.user)
#                 self.object.save()
#             except TransitionNotAllowed as e:
#                 logger.error("TransitionNotAllowed: " + str(e))
#                 raise

#         except (TransitionNotAllowed):
#             self.msg= _("submission_objectTransferEditorBeginFailure_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
#             messages.add_message(request, messages.ERROR, self.msg)
#         return redirect('/manuscript/'+str(self.object.manuscript.id))

class SubmissionSendReportView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            if not fsm_check_transition_perm(self.object.send_report, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            try:
                self.object.send_report()
                self.object.save()
            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise
            self.msg= _("submission_objectTransferEditorReturnSuccess_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
            messages.add_message(request, messages.SUCCESS, self.msg)
        except (TransitionNotAllowed):
            self.msg= _("submission_objectTransferEditorReturnFailure_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
            messages.add_message(request, messages.ERROR, self.msg)
        return redirect('/manuscript/'+str(self.object.manuscript.id))

#NOTE: for some reason, these banner messages aren't showing up.
class SubmissionFinishView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            if not fsm_check_transition_perm(self.object.finish_submission, request.user): 
                logger.debug("PermissionDenied")
                raise Http404()
            try:
                self.object.finish_submission()
                self.object.save()

                #Delete all tale copies both locally and in WT. This also deletes running instances.
                if self.object.manuscript.is_containerized() and settings.CONTAINER_DRIVER == 'wholetale':
                    wtc = w.WholeTaleCorere(admin=True)
                    for wtm_tale in wtm.Tale.objects.filter(submission=self.object, original_tale__isnull=False):
                        wtc.delete_tale(wtm_tale.wt_id)
                        wtm_tale.delete()   

                ### Messaging ###
                if(self.object._status == m.Submission.Status.RETURNED):
                    if(self.object.manuscript._status == m.Manuscript.Status.COMPLETED):
                        #If completed, send message to... editor and authors?
                        self.msg= _("submission_objectComplete_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
                        messages.add_message(request, messages.SUCCESS, self.msg)
                        recipients = m.User.objects.filter(groups__name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.object.manuscript.id)) 
                        notification_msg = _("manuscript_update_notification_forAuthor").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
                        notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
                        for u in recipients: #We have to loop to get the user model fields
                            send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
                    else:
                        #If not complete, send message to author about submitting again
                        self.msg= _("submission_objectTransferAuthorSuccess_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
                        messages.add_message(request, messages.SUCCESS, self.msg)
                        recipients = m.User.objects.filter(groups__name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.object.manuscript.id)) 
                        notification_msg = _("manuscript_objectTransferAuthor_notification_forAuthor").format(object_id=self.object.manuscript.id, object_title=self.object.manuscript.get_display_name(), object_url=self.object.manuscript.get_landing_url())
                        notify.send(request.user, verb='passed', recipient=recipients, target=self.object.manuscript, public=False, description=notification_msg)
                        for u in recipients: #We have to loop to get the user model fields
                            send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
                ### End Messaging ###

            except TransitionNotAllowed as e:
                logger.error("TransitionNotAllowed: " + str(e))
                raise

        except (TransitionNotAllowed):
            self.msg= _("submission_objectTransferAuthorFailure_banner").format(manuscript_id=self.object.manuscript.id ,manuscript_display_name=self.object.manuscript.get_display_name())
            messages.add_message(request, messages.ERROR, self.msg)
        return redirect('/manuscript/'+str(self.object.manuscript.id))

#For local containers
#This view is loaded via oauth2-proxy as an upstream. All it does is redirect to the actual notebook iframe url
#This allows us to do oauth2 outside the iframe (you can't do it inside) and then redirect to the protected notebook container viewed inside corere
#Our implementation also still preserves the ability for the notebook container to be viewed outside the iframe
class SubmissionNotebookRedirectView(LoginRequiredMixin, GetOrGenerateObjectMixin, TransitionPermissionMixin, GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    transition_method_name = 'edit_noop'
    template = 'main/notebook_redirect.html'
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if 'postauth' in request.GET:
            request.user.last_oauthproxy_forced_signin = datetime.now()
            request.user.save()
        context = {'sub_id':self.object.id,'scheme':settings.CONTAINER_PROTOCOL,'host':settings.SERVER_ADDRESS}
        return render(request, self.template, context)

class SubmissionNotebookView(LoginRequiredMixin, GetOrGenerateObjectMixin, GenericCorereObjectView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    template = 'main/notebook_iframe.html'
    #These two parameters are updated programatically in dispatch
    http_method_names = ['get', 'post']
    read_only = False
    form = f.SubmissionEmptyForm

    #We programatically check transition permissions depending on the tale in question (for WholeTale).
    #For now if not wholetale, we check if 'edit_noop'
    #code is same as in SubmissionWholeTaleEventStreamView
    def dispatch(self, request, *args, **kwargs):
        if self.object.manuscript.is_containerized() == 'Other':
            raise Http404()
        elif settings.CONTAINER_DRIVER == 'wholetale':
            self.dominant_group = w.get_dominant_group_connector(request.user, self.object)

            try:
                self.wtm_tale = self.dominant_group.groupconnector_tales.get(submission=self.object) #this will blow up and 404 if there is no dominant group, which we want
            except wtm.Tale.DoesNotExist: #We create the tale on demand if not existent. This happens because the tale is from a previous submission, or the tales were wiped out after the manuscript.compute_env was changed
                #Copy master tale, revert to previous version, launch instance.
                wtm_parent_tale = self.object.manuscript.manuscript_tales.get(original_tale=None)
                wtc = w.WholeTaleCorere(admin=True)
                wtc_tale_target_version = wtc.get_tale_version(wtm_parent_tale.wt_id, w.get_tale_version_name(self.object.version_id))
                #Ok, so I gotta copy the parent tale first and then revert it
                wtc_versioned_tale = wtc.copy_tale(tale_id=wtm_parent_tale.wt_id)
                if self.object.version_id < self.object.manuscript.get_max_submission_version_id():
                    if not wtc_tale_target_version:
                        raise Http404("The compute environment cannot be launched for this submission, because the compute environment changed after this submission was created.")
                    wtc_versioned_tale = wtc.restore_tale_to_version(wtc_versioned_tale['_id'], wtc_tale_target_version['_id'])
                self.wtm_tale = wtm.Tale.objects.create(manuscript=self.object.manuscript, submission=self.object,  wt_id=wtc_versioned_tale['_id'], group_connector=self.dominant_group, original_tale=wtm_parent_tale)
                wtc.set_group_access(self.wtm_tale.wt_id, wtc.AccessType.WRITE, self.dominant_group)

            if self.wtm_tale.original_tale == None:
                transition_method = getattr(self.object, 'edit_noop')
                if(not has_transition_perm(transition_method, request.user)):
                    print(self.dominant_group.corere_group.__dict__)

                    logger.debug("PermissionDenied")
                    raise Http404()
                else: #TODO: This form should be moved eventually to handle the non-wt workflow. Note that we only want it to show up for when authors test.
                    self.form = f.SubmissionContainerIssuesForm
            else:
                transition_method = getattr(self.object, 'view_noop')
                if(not has_transition_perm(transition_method, request.user)):
                    self.http_method_names = ['get'] 
                    self.read_only = True
                    logger.debug("PermissionDenied")
                    raise Http404()
        else:
            transition_method = getattr(self.object, 'edit_noop')
            if(not has_transition_perm(transition_method, request.user)):
                logger.debug("PermissionDenied")
                raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {'helper': self.helper, 'read_only': self.read_only, "obj_type": self.object_friendly_name, "create": self.create,
            'page_title': _("submission_notebook_pageTitle").format(submission_version=self.object.version_id),
            'page_help_text': self.page_help_text, "form": self.form,
            'manuscript_display_name': self.object.manuscript.get_display_name(), 'manuscript_id': self.object.manuscript.id, "skip_edition": self.object.manuscript.skip_edition}

        if settings.CONTAINER_DRIVER == 'wholetale': #We don't check compute_env here because it'll be handled by dispatch
            context['is_author'] = self.dominant_group.corere_group.name.startswith("Author")
            wtc = w.WholeTaleCorere(request.COOKIES.get('girderToken'))
            wtm_instance = w.get_model_instance(request.user, self.object)
            if not wtm_instance:
                wtc_instance = wtc.create_instance_with_purge(self.wtm_tale, request.user)
                wtm.Instance.objects.create(tale=self.wtm_tale, wt_id=wtc_instance['_id'], corere_user=request.user) 
            else:
                wtc_instance = wtc.get_instance_or_nothing(wtm_instance)   
                if not wtc_instance: #If the instance was deleted externally (by the user most likely)      
                    wtm_instance.delete()
                    wtc_instance = wtc.create_instance_with_purge(self.wtm_tale, request.user)
                    wtm.Instance.objects.create(tale=self.wtm_tale, wt_id=wtc_instance['_id'], corere_user=request.user) 
                elif not wtm_instance.instance_url:       
                    if(wtc_instance['status'] == w.WholeTaleCorere.InstanceStatus.ERROR):
                        #TODO-WT: Is there an error case where we want the user (author) to just skip the container entirely?
                        wtc.delete_instance(wtm_instance.wt_id)
                        wtm_instance.delete()
                        wtc_instance = wtc.create_instance_with_purge(self.wtm_tale, request.user)
                        wtm.Instance.objects.create(tale=self.wtm_tale, wt_id=wtc_instance['_id'], corere_user=request.user) 
                    elif(wtc_instance['status'] == w.WholeTaleCorere.InstanceStatus.RUNNING):
                        #If coming here later and we don't have a instance_url (because the user went away after launch) grab it.
                        #We don't do this on a new launch because there is no way it'll be ready.  
                        wtm_instance.instance_url = wtc_instance['url']
                        wtm_instance.save()
                        context['notebook_url'] = wtm_instance.get_login_container_url(request.COOKIES.get('girderToken'))
                    else: #launching
                        pass
                else:
                    context['notebook_url'] = wtm_instance.get_login_container_url(request.COOKIES.get('girderToken'))

            if wtc_instance["status"] == wtc.InstanceStatus.LAUNCHING:
                context['wt_launching'] = True #When we do status for non wt, this can probably be generalized
            else:
                context['wt_launching'] = False                
        else:
            context['notebook_url'] = self.object.manuscript.manuscript_localcontainerinfo.container_public_address()

        if not self.read_only:
            context['progress_bar_html'] = get_progress_bar_html_submission('Run Code', self.object)

        return render(request, self.template, context)

    def post(self, request, *args, **kwargs):
        #TODO: This probably needs to handle what happens if the form isn't valid?
        if request.POST.get('submit'):
            if self.form:
                if self.form.is_valid():
                    self.form.save() #This saves any launch issues reported by the author, for the curation team to review.

            return redirect('submission_info', id=self.object.id)

        if request.POST.get('back'):
            return redirect('submission_uploadfiles', id=self.object.id)

class SubmissionGenericWholeTalePermissionView(GenericCorereObjectView):
    #We programatically check transition permissions depending on the tale in question (for WholeTale).
    #For now if not wholetale, we check if 'edit_noop'
    #Code was same as in SubmissionNotebookView, but that needed more customization
    def dispatch(self, request, *args, **kwargs):
        if self.object.manuscript.is_containerized() == 'Other':
            raise Http404()
        elif settings.CONTAINER_DRIVER == 'wholetale':
            self.wtm_tale = w.get_dominant_group_connector(request.user, self.object).groupconnector_tales.get(submission=self.object)

            if self.wtm_tale.original_tale == None:
                transition_method = getattr(self.object, 'edit_noop')
                if(not has_transition_perm(transition_method, request.user)):
                    logger.debug("PermissionDenied")
                    raise Http404()
            else:
                transition_method = getattr(self.object, 'view_noop')
                if(not has_transition_perm(transition_method, request.user)):
                    self.http_method_names = ['get']
                    self.read_only = True
                    logger.debug("PermissionDenied")
                    raise Http404()
        else:
            transition_method = getattr(self.object, 'edit_noop')
            if(not has_transition_perm(transition_method, request.user)):
                logger.debug("PermissionDenied")
                raise Http404()

        return super().dispatch(request, *args, **kwargs)

# The downside to this approach is we download it to CORE2 before providing it to the user
# We could just generate the download url for the user and send them to Whole Tale directly for it.
class SubmissionDownloadWholeTaleNotebookView(LoginRequiredMixin, GetOrGenerateObjectMixin, SubmissionGenericWholeTalePermissionView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if settings.CONTAINER_DRIVER != 'wholetale': #We don't check compute_env here because it'll be handled by dispatch
            return Http404()

        wtc = w.WholeTaleCorere(request.COOKIES.get('girderToken'))
        self.dominant_group = w.get_dominant_group_connector(request.user, self.object)
        self.wtm_tale = self.dominant_group.groupconnector_tales.get(submission=self.object) #this will blow up and 404 if there is no dominant group, which we want
        tale_zip = wtc.download_tale(self.wtm_tale.wt_id)
        response = HttpResponse(tale_zip.content, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="'+self.object.manuscript.slug + '_-_submission_' + str(self.object.version_id) + '_-_whole_tale_contents_' + self.dominant_group.corere_group.name.split()[0] + '.zip"'
        return response

class SubmissionWholeTaleEventStreamView(LoginRequiredMixin, GetOrGenerateObjectMixin, SubmissionGenericWholeTalePermissionView):
    parent_reference_name = 'manuscript'
    parent_id_name = "manuscript_id"
    parent_model = m.Manuscript
    object_friendly_name = 'submission'
    model = m.Submission
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if settings.CONTAINER_DRIVER != 'wholetale': #We don't check compute_env here because it'll be handled by dispatch
            return Http404()

        wtc = w.WholeTaleCorere(request.COOKIES.get('girderToken'))
        return StreamingHttpResponse(_helper_generate_whole_tale_stream_contents(wtc, self.object, request.user, request.COOKIES.get('girderToken')))
        #return StreamingHttpResponse(_helper_fake_stream(wtc))

def _helper_generate_whole_tale_stream_contents(wtc, submission, user, girderToken):
    stream = wtc.get_event_stream()
    client = sseclient.SSEClient(stream)
    for event in client.events():
        data = json.loads(event.data)
        if data["type"] == "wt_progress":
            progress = int(data["data"]["current"] / data["data"]["total"] * 100.0)
            msg = (
                "  -> event received:"
                f" msg = {data['data']['message']}"
                f" status = {data['data']['state']}"
                f" progress = {progress}%"
            )
            yield(msg+"<br>")
            if(progress == 100):
                #In case things are still happening after the ending status message

                yield("Completing launch, should only take a moment.<br>")

                wtm_instance = w.get_model_instance(user, submission)
                wtc_instance = wtc.get_instance(wtm_instance.wt_id)
                while wtc_instance["status"] == wtc.InstanceStatus.LAUNCHING:
                    time.sleep(1)
                    wtc_instance = wtc.get_instance(wtc_instance['_id'])

                wtm_instance.instance_url = wtc_instance['url']
                wtm_instance.save()

                yield(f"Container URL: {wtm_instance.get_login_container_url(girderToken)}")
                return 

# def _helper_fake_stream(wtc):
#     for x in range(10):
#         yield(f"This is message {x} from the emergency broadcast system.<br>")
#         time.sleep(.05)
#     yield("Container URL: https://google.com")
#     return

def _helper_get_oauth_url(request, submission):
    #This code is for doing pro-active reauthentication via oauth2. We do this so that the user isn't presented with the oauth2 login inside their iframe (which they can't use).
    if(request.user.last_oauthproxy_forced_signin + timedelta(days=1) < timezone.now()):
        #We need to send the user to reauth
        container_flow_address = submission.manuscript.manuscript_localcontainerinfo.container_public_address() 
        if(request.is_secure()):
            container_flow_redirect = "https://" + settings.SERVER_ADDRESS
        else:
            container_flow_redirect = "http://" + settings.SERVER_ADDRESS
        container_flow_redirect += "/submission/" + str(submission.id) + "/notebooklogin/?postauth"
        container_flow_address += "/oauth2/sign_in?rd=" + urllib.parse.quote(container_flow_redirect, safe='')
    else:
        #We don't need to send the user to reauth
        container_flow_address = submission.manuscript.manuscript_localcontainerinfo.container_public_address() + "/submission/" + str(submission.id) + "/notebooklogin/"

    return container_flow_address

def _helper_submit_submission_and_redirect(request, submission):
    if submission._status == submission.Status.NEW or submission._status == submission.Status.REJECTED_EDITOR:
        if not fsm_check_transition_perm(submission.submit, request.user): 
            logger.debug("PermissionDenied")
            raise Http404()

        submission.submit(request.user)
        submission.save()

        if submission.manuscript.is_containerized() and settings.CONTAINER_DRIVER == 'wholetale':
            wtc = w.WholeTaleCorere(admin=True)
            tale_original = submission.submission_tales.get(original_tale=None)    
            #  Set the wt author group's access to the root tale as read
            group = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(submission.manuscript.id))
            wtc.set_group_access(tale_original.wt_id, wtc.AccessType.READ, group.wholetale_group)

            #I'm going to delete author instances here. So I need to get the authors in the group and then for each author get the instance they have
            for u in group.user_set.all():
                #TODO: This probably should be in a try catch
                u.user_instances.get(tale=tale_original).delete() #I think there should be only one tale per user per instance...

            group_editor = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(submission.manuscript.id))
            try: #Get tale if it exists. This happens when a submission was returned by an editor, as this does not create a new submission
                tale_copy_editor = wtm.Tale.objects.get(group_connector=group_editor.wholetale_group)
            except wtm.Tale.DoesNotExist:
                editor_tale_title = f"{submission.manuscript.get_display_name()} - {submission.manuscript.id} - Editor"
                wtc_tale_copy_editor = wtc.copy_tale(tale_original.wt_id, new_title=editor_tale_title)
                tale_copy_editor = wtm.Tale.objects.create(manuscript=submission.manuscript, submission=submission, wt_id=wtc_tale_copy_editor["_id"], group_connector=group_editor.wholetale_group, original_tale=tale_original)
            wtc.set_group_access(tale_copy_editor.wt_id, wtc.AccessType.WRITE, group_editor.wholetale_group)

            group_curator = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(submission.manuscript.id))
            try:
                tale_copy_curator = wtm.Tale.objects.get(group_connector=group_curator.wholetale_group)
            except wtm.Tale.DoesNotExist:
                curator_tale_title = f"{submission.manuscript.get_display_name()} - {submission.manuscript.id} - Curator"
                wtc_tale_copy_curator = wtc.copy_tale(tale_original.wt_id, new_title=curator_tale_title)
                tale_copy_curator = wtm.Tale.objects.create(manuscript=submission.manuscript, submission=submission, wt_id=wtc_tale_copy_curator["_id"], group_connector=group_curator.wholetale_group, original_tale=tale_original)
            wtc.set_group_access(tale_copy_curator.wt_id, wtc.AccessType.WRITE, group_curator.wholetale_group)

            group_verifier = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(submission.manuscript.id))
            try:
                tale_copy_verifier = wtm.Tale.objects.get(group_connector=group_verifier.wholetale_group)
            except wtm.Tale.DoesNotExist:
                verifier_tale_title = f"{submission.manuscript.get_display_name()} - {submission.manuscript.id} - Verifier"
                wtc_tale_copy_verifier = wtc.copy_tale(tale_original.wt_id, new_title=verifier_tale_title)
                tale_copy_verifier = wtm.Tale.objects.create(manuscript=submission.manuscript, submission=submission, wt_id=wtc_tale_copy_verifier["_id"], group_connector=group_verifier.wholetale_group, original_tale=tale_original)
            wtc.set_group_access(tale_copy_verifier.wt_id, wtc.AccessType.WRITE, group_verifier.wholetale_group)

        ## Messaging ###
        msg= _("submission_objectTransferEditorBeginSuccess_banner_forAuthor").format(manuscript_id=submission.manuscript.id ,manuscript_display_name=submission.manuscript.get_display_name())
        messages.add_message(request, messages.SUCCESS, msg)
        logger.info(msg)
        recipients = m.User.objects.filter(groups__name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(submission.manuscript.id)) 
        notification_msg = _("submission_objectTransfer_notification_forEditorCuratorVerifier").format(object_id=submission.manuscript.id, object_title=submission.manuscript.get_display_name(), object_url=submission.manuscript.get_landing_url())
        notify.send(request.user, verb='passed', recipient=recipients, target=submission.manuscript, public=False, description=notification_msg)
        for u in recipients: #We have to loop to get the user model fields
            send_templated_mail( template_name='test', from_email=settings.EMAIL_HOST_USER, recipient_list=[u.email], context={ 'notification_msg':notification_msg, 'user_first_name':u.first_name, 'user_last_name':u.last_name, 'user_email':u.email} )
        ## End Messaging ###

        # self.msg = _("submission_submitted_banner")
        # messages.add_message(request, messages.SUCCESS, self.msg)
        return redirect('manuscript_landing', id=submission.manuscript.id)
    else:
        #TODO: Add different message here?
        # messages.add_message(request, messages.SUCCESS, self.msg)
        return redirect('manuscript_landing', id=submission.manuscript.id)

#TODO: The error validation calling this could use refinement. It'll bail out after the first error and doesn't attach errors to file names.
def _helper_sanitary_file_check(path):
    if(path.find('..') != -1): 
        return 'File name with .. not allowed.'
    if(path.strip() == '' or (path.rsplit('/',1) and path.rsplit('/',1)[1].strip() == '')):
        return 'File name must include a character other than just spaces.'
    if(len(path) > 260):
        return 'File paths + cannot be longer than 260 characters.'    
    #TODO: Maybe include slugify check. Not using right now because that'll remove spaces among other things.
