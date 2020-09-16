import logging, os
from django import forms
from django.forms import ModelMultipleChoiceField, inlineformset_factory, TextInput
from .models import Manuscript, Submission, Edition, Curation, Verification, User, Note, GitlabFile
#from invitations.models import Invitation
from guardian.shortcuts import get_perms
from invitations.utils import get_invitation_model
from django.conf import settings
from . import constants as c
from corere.main import models as m
from django.contrib.auth.models import Group
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit
from corere.main.gitlab import helper_get_submission_branch_name
logger = logging.getLogger(__name__)

class ReadOnlyFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReadOnlyFormMixin, self).__init__(*args, **kwargs)
        
        for key in self.fields.keys():
            #print(key)
            self.fields[key].widget.attrs['readonly'] = True #May not do anything in django 2
            self.fields[key].disabled = True

    def save(self, *args, **kwargs):
        # do not do anything
        pass

class GenericFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False

class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','doi','open_data']#,'authors']

    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)

class ReadOnlyManuscriptForm(ReadOnlyFormMixin, ManuscriptForm):
    pass

#No actual editing is done in this form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
class ManuscriptFilesForm(ReadOnlyFormMixin, ManuscriptForm):
    class Meta:
        model = Manuscript
        fields = []#['title','doi','open_data']#,'authors']
    pass

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = []

    def __init__ (self, *args, **kwargs):
        super(SubmissionForm, self).__init__(*args, **kwargs)

class ReadOnlySubmissionForm(ReadOnlyFormMixin, SubmissionForm):
    pass

class GitlabFileForm(forms.ModelForm):
    class Meta:
        model = GitlabFile
        fields = ['gitlab_path']

    def __init__ (self, *args, **kwargs):
        super(GitlabFileForm, self).__init__(*args, **kwargs)
        self.fields['gitlab_path'].widget.object_instance = self.instance
        self.fields['gitlab_path'].widget.attrs['readonly'] = True
        self.fields['gitlab_sha256'].widget.attrs['readonly'] = True
        self.fields['gitlab_size'].widget.attrs['readonly'] = True
        self.fields['gitlab_date'].widget.attrs['readonly'] = True

class GitlabReadOnlyFileForm(forms.ModelForm):
    class Meta:
        model = GitlabFile
        fields = ['gitlab_path']

    def __init__ (self, *args, **kwargs):
        super(GitlabReadOnlyFileForm, self).__init__(*args, **kwargs)
        self.fields['gitlab_path'].widget.object_instance = self.instance
        self.fields['gitlab_path'].widget.attrs['readonly'] = True
        self.fields['gitlab_sha256'].widget.attrs['readonly'] = True
        self.fields['gitlab_size'].widget.attrs['readonly'] = True
        self.fields['gitlab_date'].widget.attrs['readonly'] = True
        # All fields read only
        self.fields['tag'].widget.attrs['readonly'] = True
        self.fields['description'].widget.attrs['readonly'] = True

class DownloadGitlabWidget(forms.widgets.TextInput):
    #template_name = 'django/forms/widgets/textarea.html'
    template_name = 'main/widget_download.html'

    #Here get the kwarg from the form, need to include our token or whatever we are passing
    #def get_form_kwargs()

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

GitlabFileFormSet = inlineformset_factory(
    Submission,
    GitlabFile,
    form=GitlabFileForm,
    fields=('gitlab_path','tag','description','gitlab_sha256','gitlab_size','gitlab_date'),
    extra=0,
    can_delete=False,
    widgets={
        'gitlab_path': DownloadGitlabWidget(),
        'description': TextInput() }
)

GitlabReadOnlyFileFormSet = inlineformset_factory(
    Submission,
    GitlabFile,
    form=GitlabReadOnlyFileForm,
    fields=('gitlab_path','tag','description','gitlab_sha256','gitlab_size','gitlab_date'),
    extra=0,
    can_delete=False,
    widgets={
        'gitlab_path': DownloadGitlabWidget(),
        'description': TextInput() }
)

class GitlabFileFormSetHelper(FormHelper):
     def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_class = 'form-inline'
        self.template = 'bootstrap4/table_inline_formset.html'
        self.form_tag = False
        #self.field_template = 'bootstrap4/layout/inline_field.html'
        self.layout = Layout(
            Fieldset(
            'gitlab_path',
            'tag',
            'description',
            ),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='button white')
            )
        )
        self.render_required_fields = True

#No actual editing is done in this form (files are uploaded/deleted directly with GitLab va JS)
#We just leverage the existing form infrastructure for perm checks etc
class SubmissionUploadFilesForm(ReadOnlyFormMixin, SubmissionForm):
    class Meta:
        model = Submission
        fields = []#['title','doi','open_data']#,'authors']
    pass

class EditionForm(forms.ModelForm):
    class Meta:
        model = Edition
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(EditionForm, self).__init__(*args, **kwargs)

class ReadOnlyEditionForm(ReadOnlyFormMixin, EditionForm):
    pass

class CurationForm(forms.ModelForm):
    class Meta:
        model = Curation
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(CurationForm, self).__init__(*args, **kwargs)

class ReadOnlyCurationForm(ReadOnlyFormMixin, CurationForm):
    pass

class VerificationForm(forms.ModelForm):
    class Meta:
        model = Verification
        fields = ['_status']

    def __init__ (self, *args, **kwargs):
        super(VerificationForm, self).__init__(*args, **kwargs)

class ReadOnlyVerificationForm(ReadOnlyFormMixin, VerificationForm):
    pass

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['text','scope']

    SCOPE_OPTIONS = ((role,role) for role in c.get_roles())

    scope = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                                          choices=SCOPE_OPTIONS, required=False)

    def __init__ (self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)

        #Populate scope field with existing roles
        existing_scope = []
        for role in c.get_roles():
            role_perms = get_perms(Group.objects.get(name=role), self.instance)
            if('view_note' in role_perms):
                existing_scope.append(role)
        self.fields['scope'].initial = existing_scope
        #print(self.fields['scope'].__dict__)

class CustomSelect2UserWidget(forms.SelectMultiple):
    class Media:
        js = ('main/select2_table.js',)

    def render(self, name, value, attrs=None, renderer=None):
        return super().render(name, value, attrs, renderer)

class AuthorInviteAddForm(forms.Form):
    # TODO: If we do keep this email field we should make it accept multiple. But we should probably just combine it with the choice field below
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_AUTHOR), widget=CustomSelect2UserWidget(), required=False)

class EditorAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_EDITOR), widget=CustomSelect2UserWidget(), required=False)

class CuratorAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_CURATOR), widget=CustomSelect2UserWidget(), required=False)

class VerifierAddForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_VERIFIER), widget=CustomSelect2UserWidget(), required=False)

class EditUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

#Note: not used on Authors, as we always want them assigned when created
class UserInviteForm(forms.Form):
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)
