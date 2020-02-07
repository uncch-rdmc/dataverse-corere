#from django import forms
from django import forms
from django.forms import ModelMultipleChoiceField
from .models import Manuscript, User
#from invitations.models import Invitation
from invitations.utils import get_invitation_model
from django.conf import settings
from . import constants as c
from django_select2.forms import Select2MultipleWidget

class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','note_text','doi','open_data','manuscript_file']#,'authors']

    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)
        #self.fields['editors'].queryset = User.objects.filter(groups__name=c.GROUP_ROLE_EDITOR) #MAD: check this in light of guardian

class InvitationForm(forms.Form):
    # TODO: If we do keep this email field we should make it accept multiple. But we should probably just combine it with the choice field below
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH, required=False)
    # TODO: This select2 field should be replaced with a "Heavy" one that supports Ajax calls.
    # Right now the library just pulls all usernames.
    # https://django-select2.readthedocs.io/en/latest/django_select2.html#module-django_select2.forms
    # TODO: Also, confirm that this django integration actually supports providing custom results
    # I think so if we initialize it ourselves? https://github.com/applegrew/django-select2/blob/master/docs/django_select2.rst#javascript
    existing_users = ModelMultipleChoiceField(queryset=User.objects.filter(invite_key='', groups__name=c.GROUP_ROLE_AUTHOR), widget=Select2MultipleWidget, required=False)

class NewUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
