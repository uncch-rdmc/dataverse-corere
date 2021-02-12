import logging, os, copy, sys
from django import forms
from django.forms import ModelMultipleChoiceField, inlineformset_factory, TextInput, RadioSelect, Textarea, ModelChoiceField, BaseInlineFormSet
from django.contrib.postgres.fields import ArrayField
#from .models import Manuscript, Submission, Edition, Curation, Verification, User, Note, GitFile
#from invitations.models import Invitation
from guardian.shortcuts import get_perms
from invitations.utils import get_invitation_model
from django.conf import settings
from . import constants as c
from corere.main import models as m
from django.contrib.auth.models import Group
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import FieldDoesNotExist, ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, ButtonHolder, Submit, Div
from crequest.middleware import CrequestMiddleware
from guardian.shortcuts import get_objects_for_user, assign_perm, remove_perm
logger = logging.getLogger(__name__)

### NOTE: Changing the name of any form that end in "_[ROLE]" (e.g. ManuscriptForm_Admin)
###  will break logic for generating form/formset lists

#------------ Base -------------

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

        #     Field('path', th_class="w-50"),
        #     Field('tag'),
        #     Field('description'),
        # )
        self.render_required_fields = True

list_of_roles = ["Admin","Author","Editor","Curator","Verifier"]

#Helper that adds all help text as a popover.
def tooltip_labels(model, field_strings):
    fields_html = {}
    for field_string in field_strings:
        try:
            field = model._meta.get_field(field_string)
        except FieldDoesNotExist:
            continue #if custom field we skip it

        html = '<span >'+field.verbose_name+'</span>'
        if(field.help_text != ""):
            html += '<span class="fas fa-question-circle tooltip-icon" data-toggle="tooltip" data-placement="auto" title="'+field.help_text+'"></span>'
            #html += '<button type="button" class="btn btn-secondary btn-sm" data-toggle="tooltip" data-placement="auto" title="'+field.help_text+'">?</button>'

            #html += '<a tabindex="0" role="button" data-toggle="tooltip" data-placement="auto" data-content="' + field.help_text + '"> test <span class="glyphicon glyphicon-info-sign"></span></a>'
        fields_html[field.name] = html
    return fields_html

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

#No actual editing is done in this form, just uploads
#We just leverage the existing form infrastructure for perm checks etc
class SubmissionUploadFilesForm(ReadOnlyFormMixin, forms.ModelForm):
    class Meta:
        model = m.Submission
        fields = []#['title','doi','open_data']#,'authors']
    pass

############# Manuscript Views Forms #############
#-------------

#No actual editing is done in this form, just uploads
#We just leverage the existing form infrastructure for perm checks etc
class ManuscriptFilesForm(ReadOnlyFormMixin, forms.ModelForm):
    class Meta:
        model = m.Manuscript
        fields = []#['title','doi','open_data']#,'authors']
    pass

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

#------------- Base Manuscript -------------

class ManuscriptBaseForm(forms.ModelForm):
    class Meta:
        model = m.Manuscript
        fields = ['title','pub_id','qual_analysis','qdr_review','contact_first_name','contact_last_name','contact_email',
            'description','subject','producer_first_name','producer_last_name']#, 'manuscript_authors', 'manuscript_data_sources', 'manuscript_keywords']#,'keywords','data_sources']
        labels = tooltip_labels(model, fields)

    def clean(self):
        # print(self.data)
        # print(self.instance.__dict__)
        # print(self.instance.can_begin_return_problems())

        #We run this clean if the manuscript is progressed, or after being progressed it is being edited.
        if("submit_progress_manuscript" in self.data.keys() or self.instance._status != m.Manuscript.Status.NEW):
            description = self.cleaned_data.get('description')
            if(not description):
                self.add_error('description', 'This field is required.')

            subject = self.cleaned_data.get('subject')
            if(not subject):
                self.add_error('subject', 'This field is required.')

            validation_errors = [] #we store all the "generic" errors and raise them at once
            if(self.data['author_formset-0-first_name'] == "" or self.data['author_formset-0-last_name'] == "" or self.data['author_formset-0-identifier'] == ""
                or self.data['author_formset-0-identifier_scheme'] == "" or self.data['author_formset-0-position'] == ""):
                validation_errors.append(ValidationError("You must specify an author."))
            if(self.data['data_source_formset-0-text'] == ""):
                validation_errors.append(ValidationError("You must specify a data source."))
            if(self.data['keyword_formset-0-text'] == ""):
                validation_errors.append(ValidationError("You must specify a keyword."))    

            validation_errors.extend(self.instance.can_begin_return_problems())

            if validation_errors:
                raise ValidationError(validation_errors)

            #also require a keyword, author, data source, producer(?)

#All Manuscript fields are visible to all users, so no role-based forms
class ReadOnlyManuscriptForm(ReadOnlyFormMixin, ManuscriptBaseForm):
    pass

class ManuscriptForm_Admin(ManuscriptBaseForm):
    pass

class ManuscriptForm_Author(ManuscriptBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pub_id'].disabled = True
        self.fields['qdr_review'].disabled = True

class ManuscriptForm_Editor(ManuscriptBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].disabled = True
        self.fields['subject'].disabled = True
        self.fields['contact_first_name'].disabled = True
        self.fields['contact_last_name'].disabled = True
        self.fields['contact_email'].disabled = True
        self.fields['producer_first_name'].disabled = True
        self.fields['producer_last_name'].disabled = True

class ManuscriptForm_Curator(ManuscriptBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pub_id'].disabled = True

class ManuscriptForm_Verifier(ManuscriptBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pub_id'].disabled = True
        self.fields['title'].disabled = True
        self.fields['qual_analysis'].disabled = True
        self.fields['qdr_review'].disabled = True
        self.fields['contact_first_name'].disabled = True
        self.fields['contact_last_name'].disabled = True
        self.fields['contact_email'].disabled = True
        self.fields['description'].disabled = True
        self.fields['subject'].disabled = True
        self.fields['producer_first_name'].disabled = True
        self.fields['producer_last_name'].disabled = True

ManuscriptForms = {
    "Admin": ManuscriptForm_Admin,
    "Author": ManuscriptForm_Author,
    "Editor": ManuscriptForm_Editor,
    "Curator": ManuscriptForm_Curator,
    "Verifier": ManuscriptForm_Verifier,
}
#------------- Data Source -------------

class DataSourceBaseForm(forms.ModelForm):
    class Meta:
        model = m.DataSource
        fields = ["text"]
        labels = tooltip_labels(model, fields)

class DataSourceForm_Admin(DataSourceBaseForm):
    pass

class DataSourceForm_Author(DataSourceBaseForm):
    pass

class DataSourceForm_Editor(DataSourceBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].disabled = True

class DataSourceForm_Curator(DataSourceBaseForm):
    pass

class DataSourceForm_Verifier(DataSourceBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].disabled = True

DataSourceManuscriptFormsets = {}
for role_str in list_of_roles:
    DataSourceManuscriptFormsets[role_str] = inlineformset_factory(
        m.Manuscript,
        m.DataSource,  
        extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else 0,
        form=getattr(sys.modules[__name__], "DataSourceForm_"+role_str),
        can_delete = True if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else False,
    ) 

#All Manuscript fields are visible to all users, so no role-based forms
class ReadOnlyDataSourceForm(ReadOnlyFormMixin, DataSourceBaseForm):
    pass

ReadOnlyDataSourceFormSet = inlineformset_factory(
    m.Manuscript,
    m.DataSource,  
    extra=0,
    form=ReadOnlyDataSourceForm,
    can_delete=False,
)

#------------- Keyword -------------

class KeywordBaseForm(forms.ModelForm):
    class Meta:
        model = m.Keyword
        fields = ["text"]
        labels = tooltip_labels(model, fields)

class KeywordForm_Admin(KeywordBaseForm):
    pass

class KeywordForm_Author(KeywordBaseForm):
    pass

class KeywordForm_Editor(KeywordBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].disabled = True

class KeywordForm_Curator(KeywordBaseForm):
    pass

class KeywordForm_Verifier(KeywordBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].disabled = True

KeywordManuscriptFormsets = {}
for role_str in list_of_roles:
    KeywordManuscriptFormsets[role_str] = inlineformset_factory(
        m.Manuscript,
        m.Keyword,  
        extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else 0,
        form=getattr(sys.modules[__name__], "KeywordForm_"+role_str),
        can_delete = True if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else False,
    ) 

#All Manuscript fields are visible to all users, so no role-based forms
class ReadOnlyKeywordForm(ReadOnlyFormMixin, KeywordBaseForm):
    pass

ReadOnlyKeywordFormSet = inlineformset_factory(
    m.Manuscript,
    m.Keyword,  
    extra=0,
    form=ReadOnlyKeywordForm,
    can_delete=False,
)

#------------- Author (Connected to manuscript, Not User Model) -------------

class AuthorBaseForm(forms.ModelForm):
    class Meta:
        model = m.Author
        fields = ["first_name","last_name","identifier_scheme", "identifier", "position"]
        labels = tooltip_labels(model, fields)

class AuthorForm_Admin(AuthorBaseForm):
    pass

class AuthorForm_Author(AuthorBaseForm):
    pass

class AuthorForm_Editor(AuthorBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].disabled = True
        self.fields["last_name"].disabled = True
        self.fields["identifier_scheme"].disabled = True
        self.fields["identifier"].disabled = True
        self.fields["position"].disabled = True

class AuthorForm_Curator(AuthorBaseForm):
    pass

class AuthorForm_Verifier(AuthorBaseForm):
    def __init__ (self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].disabled = True
        self.fields["last_name"].disabled = True
        self.fields["identifier_scheme"].disabled = True
        self.fields["identifier"].disabled = True
        self.fields["position"].disabled = True

class BaseAuthorManuscriptFormset(BaseInlineFormSet):
    def clean(self):
        position_list = []
        try:
            for fdata in self.cleaned_data:
                if('position' in fdata): #skip empty form
                    position_list.append(fdata['position'])
            if(len(position_list) != 0 and ( sorted(position_list) != list(range(min(position_list), max(position_list)+1)) or min(position_list) != 1)):
                raise forms.ValidationError("Positions must be consecutive whole numbers and start with 1 (e.g. [1, 2, 3, 4, 5], [3, 1, 2, 4], etc)", "error")
        except AttributeError:
            pass #sometimes there is no cleaned data

AuthorManuscriptFormsets = {}
for role_str in list_of_roles:
    AuthorManuscriptFormsets[role_str] = inlineformset_factory(
        m.Manuscript,
        m.Author,  
        extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else 0,
        form=getattr(sys.modules[__name__], "AuthorForm_"+role_str),
        can_delete = True if(role_str == "Admin" or role_str == "Author" or role_str == "Curator") else False,
        formset=BaseAuthorManuscriptFormset
    )

#All Manuscript fields are visible to all users, so no role-based forms
class ReadOnlyAuthorForm(ReadOnlyFormMixin, AuthorBaseForm):
    pass

ReadOnlyAuthorFormSet = inlineformset_factory(
    m.Manuscript,
    m.Author,  
    extra=0,
    form=ReadOnlyAuthorForm,
    can_delete=False,
)

############# Note Forms ############# (PROBABLY COLLAPSE INTO TOP)

class NoteForm(forms.ModelForm):
    class Meta:
        model = m.Note
        fields = ['text','scope','creator','note_replied_to']
        labels = tooltip_labels(model, fields)

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
            
            if(not m.Note.objects.filter(id=self.instance.id, creator=user).exists()): #If the user is not the creator of the note
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

class NoteFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'bootstrap4/table_inline_formset.html'
        self.form_tag = False
        self.form_id = 'note'
        self.render_required_fields = True

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

############# GitFile (File Metadata) Views Forms #############

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

NoteGitFileFormset = inlineformset_factory(
    m.GitFile, 
    m.Note, 
    extra=1,
    form=NoteForm,
    formset=BaseNoteFormSet,
    fields=("creator","text"),
    widgets={
        'text': Textarea(attrs={'rows':1, 'placeholder':'Write your new note...'}) }
    )

class GitFileForm(forms.ModelForm):
    class Meta:
        model = m.GitFile
        fields = ['path']

    def __init__ (self, *args, **kwargs):
        super(GitFileForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.object_instance = self.instance
        self.fields['name'].disabled = True
        self.fields['path'].disabled = True
        self.fields['md5'].disabled = True
        self.fields['size'].disabled = True
        # self.fields['date'].disabled = True

class GitFileReadOnlyFileForm(forms.ModelForm):
    class Meta:
        model = m.GitFile
        fields = ['path']

    def __init__ (self, *args, **kwargs):
        super(GitFileReadOnlyFileForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.object_instance = self.instance
        self.fields['name'].disabled = True
        self.fields['path'].disabled = True
        self.fields['md5'].disabled = True
        self.fields['size'].disabled = True
        # self.fields['date'].disabled = True
        # All fields read only
        self.fields['tag'].disabled = True
        self.fields['description'].disabled = True

class DownloadGitFileWidget(forms.widgets.TextInput):
    template_name = 'main/widget_download.html'

    def get_context(self, name, value, attrs):
        try:
            self.download_url = "/submission/"+str(self.object_instance.parent_submission.id)+"/downloadfile/?file_path="+self.object_instance.path + self.object_instance.name
        except AttributeError as e:
            logger.error("error adding download url to editfiles widget: " + str(e))
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

#Needed for another level of nesting
class NestedSubFileNoteFormSet(BaseFileNestingFormSet):
    nested_formset = NoteGitFileFormset

GitFileNoteFormSet = inlineformset_factory(
    m.Submission,
    m.GitFile,
    form=GitFileForm,
    formset=NestedSubFileNoteFormSet,
    fields=('name','path','tag','description','md5','size'),#,'date'), #TODO: REENABLE AS READONLY
    extra=0,
    can_delete=False,
    widgets={
        'name': DownloadGitFileWidget(),
        'description': Textarea(attrs={'rows':1}) }
)

GitFileReadOnlyFileNoteFormSet = inlineformset_factory(
    m.Submission,
    m.GitFile,
    form=GitFileReadOnlyFileForm,
    formset=NestedSubFileNoteFormSet,
    fields=('name','path','tag','description','md5','size'),#,'date'), #TODO: REENABLE AS READONLY
    extra=0,
    can_delete=False,
    widgets={
        'name': DownloadGitFileWidget(),
        'description': Textarea(attrs={'rows':1})}
)

class GitFileFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'main/crispy_templates/bootstrap4_table_inline_formset_custom_notes.html'
        self.form_tag = False
        self.layout = Layout(

            Field('path', th_class="w-50"),
            Field('tag'),
            Field('description'),
        )
        self.render_required_fields = True

############# Submission/Edition/Curation/Verification Views Forms #############

#------------- Base Submission -------------

# def popover_html(field):
#     html = field.verbose_name
#     if(field.help_text != ""):
#         html += '<button type="button" class="btn btn-secondary" data-toggle="tooltip" data-placement="top" title="'+field.help_text+'">?</button>'
#     return html

# def popover_html(label, content):
#     return label + '<button type="button" class="btn btn-secondary" data-toggle="tooltip" data-placement="top" title="'+content+'">?</button>'
    # ' <a tabindex="0" role="button" data-toggle="popover" data-html="true" \
    #                         data-trigger="hover" data-placement="auto" data-content="' + content + '"> \
    #                         <span class="glyphicon glyphicon-info-sign"></span></a>'

class SubmissionBaseForm(forms.ModelForm):
    class Meta:
        model = m.Submission
        fields = ['high_performance','contents_gis','contents_proprietary','contents_proprietary_sharing']
        labels = tooltip_labels(model, fields)

    #If edition/curation/verification set to "new", return error.
    def clean(self):
        if("submit_progress_edition" in self.data.keys() and self.data.get('edition_formset-0-_status','') == m.Edition.Status.NEW):
            raise ValidationError('Submission editor approval must have a status other than ' + m.Edition.Status.NEW + '.')
        if("submit_progress_curation" in self.data.keys() and self.data.get('curation_formset-0-_status','') == m.Curation.Status.NEW):
            raise ValidationError('Submission curator approval must have a status other than ' + m.Curation.Status.NEW + '.')
        if("submit_progress_verification" in self.data.keys() and self.data.get('verification_formset-0-_status','') == m.Verification.Status.NEW):
            raise ValidationError('Submission verifier approval must have a status other than ' + m.Verification.Status.NEW + '.')

class SubmissionForm_Admin(SubmissionBaseForm):
    pass

class SubmissionForm_Author(SubmissionBaseForm):
    pass

class SubmissionForm_Editor(ReadOnlyFormMixin, SubmissionBaseForm):
    pass

class SubmissionForm_Curator(ReadOnlyFormMixin, SubmissionBaseForm):
    pass

class SubmissionForm_Verifier(ReadOnlyFormMixin, SubmissionBaseForm):
    pass

SubmissionForms = {
    "Admin": SubmissionForm_Admin,
    "Author": SubmissionForm_Author,
    "Editor": SubmissionForm_Editor,
    "Curator": SubmissionForm_Curator,
    "Verifier": SubmissionForm_Verifier,
}

class ReadOnlySubmissionForm(ReadOnlyFormMixin, SubmissionBaseForm):
    pass

#------------- Edition -------------

class EditionBaseForm(forms.ModelForm):
    class Meta:
        model = m.Edition
        fields = ['report','_status']
        labels = tooltip_labels(model, fields)

class EditionForm_Admin(EditionBaseForm):
    pass

# #TODO: I'm not sure that we need an Author form for this objects, as they never see it.
# class EditionForm_Author(ReadOnlyFormMixin, EditionBaseForm):
#     class Meta:
#         model = m.Edition
#         fields = []

class EditionForm_Editor(EditionBaseForm):
    pass

class EditionForm_Curator(ReadOnlyFormMixin, EditionBaseForm):
    pass

class EditionForm_Verifier(ReadOnlyFormMixin, EditionBaseForm):
    pass

EditionSubmissionFormsets = {}
for role_str in list_of_roles:
    try:
        EditionSubmissionFormsets[role_str] = inlineformset_factory(
            m.Submission, 
            m.Edition, 
            extra=1 if(role_str == "Admin" or role_str == "Editor") else 0,
            form=getattr(sys.modules[__name__], "EditionForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

#We just hide edition entirely when its not readable, so no role-based forms
class ReadOnlyEditionForm(ReadOnlyFormMixin, EditionBaseForm):
    pass

ReadOnlyEditionSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Edition, 
    extra=0,
    form=ReadOnlyEditionForm,
    can_delete = False,
)

#------------- Curation -------------

class CurationBaseForm(forms.ModelForm):
    class Meta:
        model = m.Curation
        fields = ['report','_status']
        labels = tooltip_labels(model, fields)

class CurationForm_Admin(CurationBaseForm):
    pass

# #TODO: I'm not sure that we need an Author/Editor form for these objects, as they never see them.
# class CurationForm_Author(ReadOnlyFormMixin, CurationBaseForm):
#     class Meta:
#         model = m.Curation
#         fields = []

# #TODO: I'm not sure that we need an Author/Editor form for these objects, as they never see them.
# class CurationForm_Editor(ReadOnlyFormMixin, CurationBaseForm):
#     class Meta:
#         model = m.Curation
#         fields = []

class CurationForm_Curator(CurationBaseForm):
    pass

class CurationForm_Verifier(ReadOnlyFormMixin, CurationBaseForm):
    pass

CurationSubmissionFormsets = {}
for role_str in list_of_roles:
    try:
        CurationSubmissionFormsets[role_str] = inlineformset_factory(
            m.Submission, 
            m.Curation, 
            extra=1 if(role_str == "Admin" or role_str == "Curator") else 0,
            form=getattr(sys.modules[__name__], "CurationForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

#We just hide curation entirely when its not readable, so no role-based forms
class ReadOnlyCurationForm(ReadOnlyFormMixin, CurationBaseForm):
    pass

ReadOnlyCurationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Curation, 
    extra=0,
    form=ReadOnlyCurationForm,
    can_delete = False,
)

#------------- Verification -------------

class VerificationBaseForm(forms.ModelForm):
    class Meta:
        model = m.Verification
        fields = ['code_executability','report','_status']
        labels = tooltip_labels(model, fields)

class VerificationForm_Admin(VerificationBaseForm):
    pass

# #TODO: I'm not sure that we need an Author/Editor form for these objects, as they never see them.
# class VerificationForm_Author(ReadOnlyFormMixin, VerificationBaseForm):
#     class Meta:
#         model = m.Verification
#         fields = []

# #TODO: I'm not sure that we need an Author/Editor form for these objects, as they never see them.
# class VerificationForm_Editor(ReadOnlyFormMixin, VerificationBaseForm):
#     class Meta:
#         model = m.Verification
#         fields = []

class VerificationForm_Curator(ReadOnlyFormMixin, VerificationBaseForm):
    pass

class VerificationForm_Verifier(VerificationBaseForm):
    pass

VerificationSubmissionFormsets = {}
for role_str in list_of_roles:
    try:
        VerificationSubmissionFormsets[role_str] = inlineformset_factory(
            m.Submission, 
            m.Verification, 
            extra=1 if(role_str == "Admin" or role_str == "Verifier") else 0,
            form=getattr(sys.modules[__name__], "VerificationForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

#We just hide verification entirely when its not readable, so no role-based forms
class ReadOnlyVerificationForm(ReadOnlyFormMixin, VerificationBaseForm):
    pass

ReadOnlyVerificationSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.Verification, 
    extra=0,
    form=ReadOnlyVerificationForm,
    can_delete = False,
)

#------------ Verification Metadata - Main -------------

class VMetadataBaseForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadata
        fields = ["operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"]
        labels = tooltip_labels(model, fields)

    # def __init__ (self, *args, **kwargs):
    #     super(VMetadataForm, self).__init__(*args, **kwargs)

class VMetadataForm_Admin(VMetadataBaseForm):
    pass

class VMetadataForm_Author(VMetadataBaseForm):
    pass

class VMetadataForm_Editor(ReadOnlyFormMixin, VMetadataBaseForm):
    pass

class VMetadataForm_Curator(VMetadataBaseForm):
    pass

class VMetadataForm_Verifier(VMetadataBaseForm):
    pass

VMetadataSubmissionFormsets = {}
for role_str in list_of_roles:
    try:
        VMetadataSubmissionFormsets[role_str] = inlineformset_factory(
            m.Submission, 
            m.VerificationMetadata, 
            extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator" or role_str == "Verifier") else 0,
            form=getattr(sys.modules[__name__], "VMetadataForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

class ReadOnlyVMetadataForm(ReadOnlyFormMixin, VMetadataBaseForm):
    pass

ReadOnlyVMetadataSubmissionFormset = inlineformset_factory(
    m.Submission, 
    m.VerificationMetadata, 
    extra=0,
    form=ReadOnlyVMetadataForm,
    can_delete = False,
)

# VMetadataSubmissionFormset = inlineformset_factory(
#     m.Submission,
#     m.VerificationMetadata,  
#     extra=1,
#     form=VMetadataForm,
#     fields=("operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"),
#     can_delete = True,
# )

#------------ Verification Metadata - Package -------------

class VMetadataPackageBaseForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataPackage
        fields = ["name","version", "source_default_repo", "source_cran", "source_author_website", "source_dataverse", "source_other"]
        labels = tooltip_labels(model, fields)

    # def __init__ (self, *args, **kwargs):
    #     super(VMetadataPackageForm, self).__init__(*args, **kwargs)

class VMetadataPackageForm_Admin(VMetadataPackageBaseForm):
    pass

class VMetadataPackageForm_Author(VMetadataPackageBaseForm):
    pass

class VMetadataPackageForm_Editor(ReadOnlyFormMixin, VMetadataPackageBaseForm):
    pass

class VMetadataPackageForm_Curator(VMetadataPackageBaseForm):
    pass

class VMetadataPackageForm_Verifier(VMetadataPackageBaseForm):
    pass

VMetadataPackageVMetadataFormsets = {}
for role_str in list_of_roles:
    try:
        VMetadataPackageVMetadataFormsets[role_str] = inlineformset_factory(
            m.VerificationMetadata,  
            m.VerificationMetadataPackage,  
            extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator" or role_str == "Verifier") else 0,
            form=getattr(sys.modules[__name__], "VMetadataPackageForm_"+role_str),
            can_delete = True,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

class ReadOnlyVMetadataPackageForm(ReadOnlyFormMixin, VMetadataPackageBaseForm):
    pass

ReadOnlyVMetadataPackageVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataPackage,  
    extra=0,
    form=ReadOnlyVMetadataPackageForm,
    can_delete = False,
)


# VMetadataPackageVMetadataFormset = inlineformset_factory(
#     m.VerificationMetadata,  
#     m.VerificationMetadataPackage,  
#     extra=1,
#     form=VMetadataPackageForm,
#     fields=("name","version", "source_default_repo", "source_cran", "source_author_website", "source_dataverse", "source_other"),
#     can_delete = True,
# )

#------------ Verification Metadata - Software -------------

class VMetadataSoftwareBaseForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataSoftware
        fields = ["name","version", "code_repo_url"]
        labels = tooltip_labels(model, fields)

    # def __init__ (self, *args, **kwargs):
    #     super(VMetadataSoftwareForm, self).__init__(*args, **kwargs)

class VMetadataSoftwareForm_Admin(VMetadataSoftwareBaseForm):
    pass

class VMetadataSoftwareForm_Author(VMetadataSoftwareBaseForm):
    pass

class VMetadataSoftwareForm_Editor(ReadOnlyFormMixin, VMetadataSoftwareBaseForm):
    pass

class VMetadataSoftwareForm_Curator(VMetadataSoftwareBaseForm):
    pass

class VMetadataSoftwareForm_Verifier(VMetadataSoftwareBaseForm):
    pass

VMetadataSoftwareVMetadataFormsets = {}
for role_str in list_of_roles:
    try:
        VMetadataSoftwareVMetadataFormsets[role_str] = inlineformset_factory(
            m.VerificationMetadata,  
            m.VerificationMetadataSoftware,  
            extra=1 if(role_str == "Admin" or role_str == "Author" or role_str == "Curator" or role_str == "Verifier") else 0,
            form=getattr(sys.modules[__name__], "VMetadataSoftwareForm_"+role_str),
            can_delete = True,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

# VMetadataSoftwareVMetadataFormset = inlineformset_factory(
#     m.VerificationMetadata,  
#     m.VerificationMetadataSoftware,  
#     extra=1,
#     form=VMetadataSoftwareForm,
#     fields=("name","version", "code_repo_url"),
#     can_delete = True,
# )

class ReadOnlyVMetadataSoftwareForm(ReadOnlyFormMixin, VMetadataSoftwareBaseForm):
    pass

ReadOnlyVMetadataSoftwareVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataSoftware,  
    extra=0,
    form=ReadOnlyVMetadataSoftwareForm,
    can_delete = False,
)

#------------ Verification Metadata - Badge -------------

class VMetadataBadgeBaseForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataBadge
        fields = ["name","badge_type","version","definition_url","logo_url","issuing_org","issuing_date","verification_metadata"]
        labels = tooltip_labels(model, fields)

    # def __init__ (self, *args, **kwargs):
    #     super(VMetadataBadgeForm, self).__init__(*args, **kwargs)

class VMetadataBadgeForm_Admin(VMetadataBadgeBaseForm):
    pass

class VMetadataBadgeForm_Curator(VMetadataBadgeBaseForm):
    pass

#No forms for other roles as they cannot view

VMetadataBadgeVMetadataFormsets = {}
for role_str in list_of_roles:
    try:
        VMetadataBadgeVMetadataFormsets[role_str] = inlineformset_factory(
            m.VerificationMetadata,  
            m.VerificationMetadataBadge,  
            extra=1 if(role_str == "Admin" or role_str == "Curator" ) else 0,
            form=getattr(sys.modules[__name__], "VMetadataBadgeForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass

# VMetadataBadgeVMetadataFormset = inlineformset_factory(
#     m.VerificationMetadata,  
#     m.VerificationMetadataBadge,  
#     extra=1,
#     form=VMetadataBadgeForm,
#     fields=("name","type","version","definition_url","logo_url","issuing_org","issuing_date","verification_metadata"),
#     can_delete = True,
# )

class ReadOnlyVMetadataBadgeForm(ReadOnlyFormMixin, VMetadataBadgeBaseForm):
    pass

ReadOnlyVMetadataBadgeVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataBadge,  
    extra=0,
    form=ReadOnlyVMetadataBadgeForm,
    can_delete = False,
)

#------------ Verification Metadata - Audit -------------

class VMetadataAuditBaseForm(forms.ModelForm):
    class Meta:
        model = m.VerificationMetadataAudit
        fields = ["name","version","url","organization","verified_results","exceptions","exception_reason"]
        labels = tooltip_labels(model, fields)

    # def __init__ (self, *args, **kwargs):
    #     super(VMetadataAuditForm, self).__init__(*args, **kwargs)


class VMetadataAuditForm_Admin(VMetadataAuditBaseForm):
    pass

class VMetadataAuditForm_Curator(VMetadataAuditBaseForm):
    pass

#No forms for other roles as they cannot view

VMetadataAuditVMetadataFormsets = {}
for role_str in list_of_roles:
    try:
        VMetadataAuditVMetadataFormsets[role_str] = inlineformset_factory(
            m.VerificationMetadata,  
            m.VerificationMetadataAudit,  
            extra=1 if(role_str == "Admin" or role_str == "Curator") else 0,
            form=getattr(sys.modules[__name__], "VMetadataAuditForm_"+role_str),
            can_delete = False,
        ) 
    except AttributeError:
        pass #If no form for role we should never show the form, so pass


# VMetadataAuditVMetadataFormset = inlineformset_factory(
#     m.VerificationMetadata,  
#     m.VerificationMetadataAudit,  
#     extra=1,
#     form=VMetadataAuditForm,
#     fields=("name","version","url","organization","verified_results","code_executability","exceptions","exception_reason"),
#     can_delete = True,
# )

class ReadOnlyVMetadataAuditForm(ReadOnlyFormMixin, VMetadataAuditBaseForm):
    pass

ReadOnlyVMetadataAuditVMetadataFormset = inlineformset_factory(
    m.VerificationMetadata,  
    m.VerificationMetadataAudit,  
    extra=0,
    form=ReadOnlyVMetadataAuditForm,
    can_delete = False,
)








#OK, so my code is able to create a new form with changed fields and then pass it to a dynamically created formset
#The next question becomes whether its really worth it?
#... well, we can use the "non-dynamic" forms for admin and just generate one for each of the four roles
#... meh, I think its actually better to just re-define the form for admin with no changes
#... This also scales ok because it preserves any other configuration done in the base form
#... ... Well except for the formset_factory which is defined twice currently. Maybe I can use type() to subclass it as well.
#... ... Doesn't seem to work as expected. I don't understand factory functions

# What is my plan?
# Define all forms manually, using inheritance
# Define formsets programatically, using type?






##### SEMI WORKING TEST

# testfactorydict = {}
# for x in range(5):
#     afield = VMetadataForm.base_fields['operating_system']
#     afield.disabled = True
#     field_defs = {
#         'operating_system': afield
#         }
#     DynamicFormClass = type("DynamicForm"+str(x), (VMetadataForm,), field_defs)

#     # formset_defs = {
#     #     'form': DynamicFormClass
#     #     }
#     # testfactorydict[str(x)] = type("DynamicFormset"+str(x), (VMetadataSubmissionFormset,), formset_defs)
#     testfactorydict[str(x)] = inlineformset_factory(
#         m.Submission,
#         m.VerificationMetadata,  
#         extra=1,
#         form=VMetadataForm,
#         fields=("operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"),
#         can_delete = True,
#     )


##### NOT WORKING JUNK

#Input: takes your inlineformset_factory, a list of disabled fields, a list of fields to remove
#Output: a new inlineformset_factory with these fields changed
# def inlineformset_factory_restrictor(if_factory, disable_fields, remove_fields):
#     altered_if_factory = copy.deepcopy(if_factory)
#     altered_if_form = copy.deepcopy(altered_if_factory.form)
#     #print(altered_if_factory.form.base_fields)
#     altered_if_factory.form = altered_if_form
#     #altered_if_factory.form.base_fields['host_url'].disabled = True
#     return altered_if_factory  

#VMetadataSubmissionFormsetRestrictTest = inlineformset_factory_restrictor(VMetadataSubmissionFormset, [], [])

    #testfactorydict[str(x)] = VMetadataSubmissionFormset

    # testfactorydict[str(x)] = inlineformset_factory(
    #     m.Submission,
    #     m.VerificationMetadata,  
    #     extra=1,
    #     form=DynamicFormClass,
    #     fields=("operating_system","machine_type", "scheduler", "platform", "processor_reqs", "host_url", "memory_reqs"),
    #     can_delete = True,
    # )


# class GitFileForm(forms.ModelForm):
#     class Meta:
#         model = m.GitFile
#         fields = ['path']

#     def __init__ (self, *args, **kwargs):
#         super(GitFileForm, self).__init__(*args, **kwargs)
#         self.fields['path'].widget.object_instance = self.instance
#         self.fields['path'].disabled = True
#         self.fields['md5'].disabled = True
#         self.fields['size'].disabled = True
#         self.fields['date'].disabled = True