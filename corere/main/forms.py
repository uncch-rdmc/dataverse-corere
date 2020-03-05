#from django import forms
from django import forms
from django.forms import ModelMultipleChoiceField
from .models import Manuscript, Submission, Verification, Curation, User, Note
#from invitations.models import Invitation
from guardian.shortcuts import get_perms
from invitations.utils import get_invitation_model
from django.conf import settings
from . import constants as c
from django_select2.forms import Select2MultipleWidget
from django.contrib.auth.models import Group

class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','doi','open_data']#,'authors']

    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = []

    def __init__ (self, *args, **kwargs):
        super(SubmissionForm, self).__init__(*args, **kwargs)

class VerificationForm(forms.ModelForm):
    class Meta:
        model = Verification
        fields = ['status']

    def __init__ (self, *args, **kwargs):
        super(VerificationForm, self).__init__(*args, **kwargs)

class CurationForm(forms.ModelForm):
    class Meta:
        model = Curation
        fields = ['status']

    def __init__ (self, *args, **kwargs):
        super(CurationForm, self).__init__(*args, **kwargs)

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

class AuthorInvitationForm(forms.Form):
    # TODO: If we do keep this email field we should make it accept multiple. But we should probably just combine it with the choice field below
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)

    # TODO: This select2 field should be replaced with a "Heavy" one that supports Ajax calls.
    # Right now the library just pulls all usernames.
    # https://django-select2.readthedocs.io/en/latest/django_select2.html#module-django_select2.forms
    # 
    # Also, confirm that this django integration actually supports providing custom results
    # I think so if we initialize it ourselves? https://github.com/applegrew/django-select2/blob/master/docs/django_select2.rst#javascript
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_AUTHOR), widget=Select2MultipleWidget, required=False)

class CuratorInvitationForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_CURATOR), widget=Select2MultipleWidget, required=False)

class VerifierInvitationForm(forms.Form):
    users_to_add = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_VERIFIER), widget=Select2MultipleWidget, required=False)

class NewUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
