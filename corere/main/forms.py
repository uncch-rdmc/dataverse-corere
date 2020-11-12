import logging, os
from django import forms
from django.forms import ModelMultipleChoiceField, inlineformset_factory, TextInput, RadioSelect, Textarea, ModelChoiceField
from django.contrib.postgres.fields import ArrayField
#from .models import Manuscript, Submission, Edition, Curation, Verification, User, Note, GitlabFile
#from invitations.models import Invitation
from guardian.shortcuts import get_perms
from invitations.utils import get_invitation_model
from django.conf import settings
from . import constants as c
from corere.main import models as m
from django.contrib.auth.models import Group
from django.forms.models import BaseInlineFormSet
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, ButtonHolder, Submit, Div
from corere.main.gitlab import helper_get_submission_branch_name
from crequest.middleware import CrequestMiddleware
from guardian.shortcuts import get_objects_for_user, assign_perm, remove_perm
logger = logging.getLogger(__name__)

class ReadOnlyFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReadOnlyFormMixin, self).__init__(*args, **kwargs)
        
        for key in self.fields.keys():
            self.fields[key].disabled = True

    def save(self, *args, **kwargs):
        pass # do not do anything

class GenericFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False

class ManuscriptFormHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False

        self.layout = Layout(
            'title','pub_id','description','subject',
            Div(
                Div('qual_analysis',css_class='col-md-6',),
                Div('qdr_review',css_class='col-md-6',),
                css_class='row',
            ),
            Div(
                Div('producer_first_name',css_class='col-md-6',),
                Div('producer_last_name',css_class='col-md-6',),
                css_class='row',
            ),
            Div(
                Div('contact_first_name',css_class='col-md-6',),
                Div('contact_last_name',css_class='col-md-6',),
                Div('contact_email',css_class='col-md-6',),
                css_class='row',
            )
        )

class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = m.Manuscript
        fields = ['title','pub_id','qual_analysis','qdr_review','contact_first_name','contact_last_name','contact_email',
            'description','subject','producer_first_name','producer_last_name']#, 'manuscript_authors', 'manuscript_data_sources', 'manuscript_keywords']#,'keywords','data_sources']
    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)

class ReadOnlyManuscriptForm(ReadOnlyFormMixin, ManuscriptForm):
    pass

#No actual editing is done in this form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
class ManuscriptFilesForm(ReadOnlyFormMixin, ManuscriptForm):
    class Meta:
        model = m.Manuscript
        fields = []#['title','doi','open_data']#,'authors']
    pass

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = m.Submission
        fields = ['high_performance','contents_gis','contents_proprietary','contents_proprietary_sharing']

    def __init__ (self, *args, **kwargs):
        super(SubmissionForm, self).__init__(*args, **kwargs)

class ReadOnlySubmissionForm(ReadOnlyFormMixin, SubmissionForm):
    pass

#------------ Note -------------

class NoteForm(forms.ModelForm):
    class Meta:
        model = m.Note
        fields = ['text','scope','creator','note_replied_to']

    SCOPE_OPTIONS = (('public','Public'),('private','Private'))

    scope = forms.ChoiceField(widget=forms.RadioSelect,
                                        choices=SCOPE_OPTIONS, required=False)

    def __init__ (self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
        #For some reason I can't fathom, accessing any note info via self.instance causes many extra calls to this method.
        #It also causes the end form to not populate. So we are getting the info we need on the manuscript via crequest

        user = CrequestMiddleware.get_request().user
        path_obj_name = CrequestMiddleware.get_request().resolver_match.url_name.split("_")[0] #CrequestMiddleware.get_request().resolver_match.func.view_class.object_friendly_name
        try:
            path_obj_id = CrequestMiddleware.get_request().resolver_match.kwargs['id']
            if(path_obj_name == "submission"):
                manuscript = m.Submission.objects.get(id=path_obj_id).manuscript
            elif(path_obj_name == "edition"):
                manuscript = m.Edition.objects.get(id=path_obj_id).submission.manuscript
            elif(path_obj_name == "curation"):
                manuscript = m.Curation.objects.get(id=path_obj_id).submission.manuscript
            elif(path_obj_name == "verification"):
                manuscript = m.Verification.objects.get(id=path_obj_id).submission.manuscript
            else:
                raise TypeError("Object name parsed from url string for note form does not match our lookup")
        except KeyError: #during creation, id we want is different
            try: #creating a sub on a manuscript
                manuscript = m.Manuscript.objects.get(id=CrequestMiddleware.get_request().resolver_match.kwargs['manuscript_id'])
            except KeyError: #creating a edition/curation/verification on a submission
                try:
                    manuscript = m.Submission.objects.get(id=CrequestMiddleware.get_request().resolver_match.kwargs['submission_id']).manuscript
                except KeyError:
                    raise TypeError("Object name parsed from url string for note form does not match our lookup, during create")

        if(not (user.has_any_perm(c.PERM_MANU_CURATE, manuscript) or user.has_any_perm(c.PERM_MANU_VERIFY, manuscript))):
            self.fields.pop('scope')
        else:       
            #Populate scope field depending on existing roles
            existing_roles = []
            for role in c.get_roles():
                role_perms = get_perms(Group.objects.get(name=role), self.instance)
                if(c.PERM_NOTE_VIEW_N in role_perms):
                    existing_roles.append(role)
            if(len(existing_roles) == len(c.get_roles())): #pretty crude check, if all roles then its public
                self.fields['scope'].initial = 'public'
            else:
                self.fields['scope'].initial = 'private'

        self.fields['creator'].disabled = True
        if(self.instance.id): #if based off existing note
            
            if(not Note.objects.filter(id=self.instance.id, creator=user).exists()): #If the user is not the creator of the note
                for fkey, fval in self.fields.items():
                    fval.widget.attrs['disabled']=True #you have to disable this way for scope to disable

    def save(self, commit, *args, **kwargs):
        if(self.has_changed()):
            user = CrequestMiddleware.get_request().user
            if(self.cleaned_data['creator'] != user):
                pass #Do not save
        super(NoteForm, self).save(commit, *args, **kwargs)
        if('scope' in self.changed_data):
            #Somewhat inefficient, but we just delete all perms and readd new ones. Safest.
            for role in c.get_roles():
                group = Group.objects.get(name=role)
                remove_perm(c.PERM_NOTE_VIEW_N, group, self.instance)
            if(self.cleaned_data['scope'] == 'public'):
                for role in c.get_roles():
                    group = Group.objects.get(name=role)
                    assign_perm(c.PERM_NOTE_VIEW_N, group, self.instance)
            else:
                if(user.has_any_perm(c.PERM_MANU_CURATE, self.instance.manuscript) or user.has_any_perm(c.PERM_MANU_VERIFY, self.instance.manuscript)): #only users with certain roles can set private
                    for role in c.get_private_roles():
                        group = Group.objects.get(name=role)
                        assign_perm(c.PERM_NOTE_VIEW_N, group, self.instance)
                else:
                    #At this point we've saved already, maybe we shouldn't?
                    logger.warning("User id:{0} attempted to set note id:{1} to private, when they do not have the required permissions. They may have tried hacking the form.".format(user.id, self.instance.id))
                    raise Http404()

#TODO: Making this generic may have been pointless, not sure if its needed?
class BaseFileNestingFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super(BaseFileNestingFormSet, self).add_fields(form, index)
        # save the formset in the 'nested' property
        form.nested = self.nested_formset(
            instance=form.instance,
            data=form.data if form.is_bound else None,
            files=form.files if form.is_bound else None,
            prefix='note-%s-%s' % (
                form.prefix,
                self.nested_formset.get_default_prefix()), #Defining prefix seems nessecary for getting save to work
        )
    
    def is_valid(self):
        result = super(BaseFileNestingFormSet, self).is_valid()
        if self.is_bound:
            for form in self.forms:
                if hasattr(form, 'nested'):
                    result = result and form.nested.is_valid()
        return result

    def save(self, commit=True):
        result = super(BaseFileNestingFormSet, self).save(commit=commit)
        for form in self.forms:
            if hasattr(form, 'nested'):
                if not self._should_delete_form(form):
                    form.nested.save(commit=commit)
        return result

class BaseNoteFormSet(BaseInlineFormSet):

    #only allow deleting of user-owned notes. we also disable the checkbox via JS
    @property
    def deleted_forms(self):
        deleted_forms = super(BaseNoteFormSet, self).deleted_forms
        user = CrequestMiddleware.get_request().user
        for i, form in enumerate(deleted_forms):
            if(not Note.objects.filter(id=form.instance.id, creator=user).exists()): #If the user is not the creator of the note
                deleted_forms.pop(i) #Then we remove the note from the delete list, to not delete the note

        return deleted_forms

    #only show private notes if user is curator/verifier on manuscript
    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            self._queryset = get_objects_for_user(CrequestMiddleware.get_request().user, c.PERM_NOTE_VIEW_N, klass=self.queryset.filter())
            if not self._queryset.ordered:
                self._queryset = self._queryset.order_by(self.model._meta.pk.name)                
        return self._queryset
        

NoteGitlabFileFormset = inlineformset_factory(
    m.GitlabFile, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

#Needed for another level of nesting
class NestedSubFileNoteFormSet(BaseFileNestingFormSet):
    nested_formset = NoteGitlabFileFormset

NoteSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

NoteEditionFormset = inlineformset_factory(
    m.Edition, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

NoteCurationFormset = inlineformset_factory(
    m.Curation, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        # 'creator': CreatorChoiceField(),
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

NoteVerificationFormset = inlineformset_factory(
    m.Verification, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

#------------ GitlabFile -------------

class GitlabFileForm(forms.ModelForm):
    class Meta:
        model = m.GitlabFile
        fields = ['gitlab_path']

    def __init__ (self, *args, **kwargs):
        super(GitlabFileForm, self).__init__(*args, **kwargs)
        self.fields['gitlab_path'].widget.object_instance = self.instance
        self.fields['gitlab_path'].disabled = True
        self.fields['gitlab_sha256'].disabled = True
        self.fields['gitlab_size'].disabled = True
        self.fields['gitlab_date'].disabled = True

class GitlabReadOnlyFileForm(forms.ModelForm):
    class Meta:
        model = m.GitlabFile
        fields = ['gitlab_path']

    def __init__ (self, *args, **kwargs):
        super(GitlabReadOnlyFileForm, self).__init__(*args, **kwargs)
        self.fields['gitlab_path'].widget.object_instance = self.instance
        self.fields['gitlab_path'].disabled = True
        self.fields['gitlab_sha256'].disabled = True
        self.fields['gitlab_size'].disabled = True
        self.fields['gitlab_date'].disabled = True
        # All fields read only
        self.fields['tag'].disabled = True
        self.fields['description'].disabled = True

class DownloadGitlabWidget(forms.widgets.TextInput):
    template_name = 'main/widget_download.html'

    def get_context(self, name, value, attrs):
        try:
            #TODO: If root changes in our env variables this will break
            #TODO: When adding the user tokens, fill them in via javascript as user is a pita to get here
            self.download_url = os.environ["GIT_LAB_URL"] + "/root/" + self.object_instance.parent_submission.manuscript.gitlab_submissions_path \
                + "/-/raw/" + helper_get_submission_branch_name(self.object_instance.parent_submission.manuscript) + "/" + self.object_instance.gitlab_path+"?inline=false"+"&private_token="+os.environ["GIT_PRIVATE_ADMIN_TOKEN"]
        except AttributeError as e:
            self.download_url = ""
        return {
            'widget': {
                'name': name,
                'is_hidden': self.is_hidden,
                'required': self.is_required,
                'value': self.format_value(value),
                'attrs': self.build_attrs(self.attrs, attrs),
                'template_name': self.template_name,
                'download_url': self.download_url 
            },
        }

GitlabFileNoteFormSet = inlineformset_factory(
    m.Submission,
    m.GitlabFile,
    form=GitlabFileForm,
    formset=NestedSubFileNoteFormSet,
    fields=('gitlab_path','tag','description','gitlab_sha256','gitlab_size','gitlab_date'), #'fakefield'),
    extra=1,
    can_delete=False,
    widgets={
        'gitlab_path': DownloadGitlabWidget(),
        'description': Textarea(attrs={'rows':1}) }
)

GitlabReadOnlyFileNoteFormSet = inlineformset_factory(
    m.Submission,
    m.GitlabFile,
    form=GitlabReadOnlyFileForm,
    formset=NestedSubFileNoteFormSet,
    fields=('gitlab_path','tag','description','gitlab_sha256','gitlab_size','gitlab_date'),
    extra=1,
    can_delete=False,
    widgets={
        'gitlab_path': DownloadGitlabWidget(),
        'description': Textarea(attrs={'rows':1})}
)

class GitlabFileFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'main/crispy_templates/bootstrap4_table_inline_formset_custom_notes.html'
        self.form_tag = False
        self.layout = Layout(

            Field('gitlab_path', th_class="w-50"),
            Field('tag'),
            Field('description'),
        )
        self.render_required_fields = True

#-------------------------

class NoteFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'bootstrap4/table_inline_formset.html'
        self.form_tag = False
        self.form_id = 'note'
        self.render_required_fields = True

#No actual editing is done in this form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
class SubmissionUploadFilesForm(ReadOnlyFormMixin, SubmissionForm):
    class Meta:
        model = m.Submission
        fields = []#['title','doi','open_data']#,'authors']
    pass

class EditionForm(forms.ModelForm):
    class Meta:
        model = m.Edition
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(EditionForm, self).__init__(*args, **kwargs)

class ReadOnlyEditionForm(ReadOnlyFormMixin, EditionForm):
    pass

class CurationForm(forms.ModelForm):
    class Meta:
        model = m.Curation
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(CurationForm, self).__init__(*args, **kwargs)

class ReadOnlyCurationForm(ReadOnlyFormMixin, CurationForm):
    pass

class VerificationForm(forms.ModelForm):
    class Meta:
        model = m.Verification
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(VerificationForm, self).__init__(*args, **kwargs)

class ReadOnlyVerificationForm(ReadOnlyFormMixin, VerificationForm):
    pass

#-------------------------

class CustomSelect2UserWidget(forms.SelectMultiple):
    class Media:
        js = ('main/select2_table.js',)

    def render(self, name, value, attrs=None, renderer=None):
        return super().render(name, value, attrs, renderer)

class AuthorInviteAddForm(forms.Form):
    # TODO: If we do keep this email field we should make it accept multiple. But we should probably just combine it with the choice field below
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)
    users_to_add = ModelMultipleChoiceField(queryset=m.User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_AUTHOR), widget=CustomSelect2UserWidget(), required=False)

class EditorAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=m.User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_EDITOR), widget=CustomSelect2UserWidget(), required=False)

class CuratorAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=m.User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_CURATOR), widget=CustomSelect2UserWidget(), required=False)

class VerifierAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=m.User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_VERIFIER), widget=CustomSelect2UserWidget(), required=False)

class EditUserForm(forms.ModelForm):
    class Meta:
        model = m.User
        fields = ['username', 'email', 'first_name', 'last_name']

#Note: not used on Authors, as we always want them assigned when created
class UserInviteForm(forms.Form):
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)


EditionSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Edition, 
    extra=1,
    form=EditionForm,
    fields=("_status",),
    can_delete = False,
)

ReadOnlyEditionSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Edition, 
    extra=1,
    form=ReadOnlyEditionForm,
    fields=("_status",),
    can_delete = False,
)

CurationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Curation, 
    extra=1,
    form=CurationForm,
    fields=("_status",),
    can_delete = False,
)

ReadOnlyCurationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Curation, 
    extra=1,
    form=ReadOnlyCurationForm,
    fields=("_status",),
    can_delete = False,
)

VerificationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Verification, 
    extra=1,
    form=VerificationForm,
    fields=("_status",),
    can_delete = False,
)

ReadOnlyVerificationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Verification, 
    extra=1,
    form=ReadOnlyVerificationForm,
    fields=("_status",),
    can_delete = False,
)

####### MANUSCRIPT ######

class GenericInlineFormSetHelper(FormHelper):
     def __init__(self, form_id="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'bootstrap4/table_inline_formset.html'#'main/crispy_templates/bootstrap4_table_inline_formset_custom_notes.html'
        self.form_tag = False
        # if 'form_id' in kwargs:
        self.form_id = form_id
        # self.layout = Layout(

        #     Field('gitlab_path', th_class="w-50"),
        #     Field('tag'),
        #     Field('description'),
        # )
        self.render_required_fields = True

class AuthorForm(forms.ModelForm):
    class Meta:
        model = m.Author
        fields = ["first_name","last_name","identifier_scheme", "identifier", "position"]

    def __init__ (self, *args, **kwargs):
        super(AuthorForm, self).__init__(*args, **kwargs)

AuthorManuscriptFormset = inlineformset_factory(
    m.Manuscript,
    m.Author,  
    extra=1,
    form=AuthorForm,
    fields=("first_name","last_name","identifier_scheme", "identifier", "position"),
    can_delete = True,
)

class DataSourceForm(forms.ModelForm):
    class Meta:
        model = m.DataSource
        fields = ["text"]

    def __init__ (self, *args, **kwargs):
        super(DataSourceForm, self).__init__(*args, **kwargs)

DataSourceManuscriptFormset = inlineformset_factory(
    m.Manuscript,
    m.DataSource,  
    extra=1,
    form=DataSourceForm,
    fields=("text",),
    can_delete = True,
)

class KeywordForm(forms.ModelForm):
    class Meta:
        model = m.Keyword
        fields = ["text"]

    def __init__ (self, *args, **kwargs):
        super(KeywordForm, self).__init__(*args, **kwargs)

KeywordManuscriptFormset = inlineformset_factory(
    m.Manuscript,
    m.Keyword,  
    extra=1,
    form=KeywordForm,
    fields=("text",),
    can_delete = True,
)

class VMetadataPackageForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataPackage
        fields = ["name","version", "source_default_repo", "source_cran", "source_author_website", "source_dataverse", "source_other"]

    def __init__ (self, *args, **kwargs):
        super(VMetadataPackageForm, self).__init__(*args, **kwargs)

VMetadataPackageVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataPackage,  
    extra=1,
    form=VMetadataPackageForm,
    fields=("name","version", "source_default_repo", "source_cran", "source_author_website", "source_dataverse", "source_other"),
    can_delete = True,
)

class VMetadataSoftwareForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataSoftware
        fields = ["name","version", "code_repo_url"]

    def __init__ (self, *args, **kwargs):
        super(VMetadataSoftwareForm, self).__init__(*args, **kwargs)

VMetadataSoftwareVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataSoftware,  
    extra=1,
    form=VMetadataSoftwareForm,
    fields=("name","version", "code_repo_url"),
    can_delete = True,
)

class VMetadataBadgeForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataBadge
        fields = ["name","type","version","definition_url","logo_url","issuing_org","issuing_date","verification_metadata"]

    def __init__ (self, *args, **kwargs):
        super(VMetadataBadgeForm, self).__init__(*args, **kwargs)

VMetadataBadgeVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataBadge,  
    extra=1,
    form=VMetadataBadgeForm,
    fields=("name","type","version","definition_url","logo_url","issuing_org","issuing_date","verification_metadata"),
    can_delete = True,
)

class VMetadataAuditForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataAudit
        fields = ["name","version","url","organization","verified_results","code_executability","exceptions","exception_reason"]

    def __init__ (self, *args, **kwargs):
        super(VMetadataAuditForm, self).__init__(*args, **kwargs)

VMetadataAuditVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataAudit,  
    extra=1,
    form=VMetadataAuditForm,
    fields=("name","version","url","organization","verified_results","code_executability","exceptions","exception_reason"),
    can_delete = True,
)

class VMetadataForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadata
        fields = ["operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"]

    def __init__ (self, *args, **kwargs):
        super(VMetadataForm, self).__init__(*args, **kwargs)

VMetadataSubmissionFormset = inlineformset_factory(
    m.Submission,
    m.VerificationMetadata,  
    extra=1,
    form=VMetadataForm,
    fields=("operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"),
    can_delete = True,
)
