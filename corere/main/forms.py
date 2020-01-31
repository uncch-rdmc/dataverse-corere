#from django import forms
from django import forms
from .models import Manuscript, User
#from invitations.models import Invitation
from invitations.utils import get_invitation_model
from django.conf import settings

class ManuscriptForm(forms.ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','note_text','doi','open_data','editors','manuscript_file']

    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)
        self.fields['editors'].queryset = User.objects.filter(is_editor=True)

class InvitationForm(forms.Form):
    email = forms.CharField(label='Invitee email', max_length=settings.INVITATIONS_EMAIL_MAX_LENGTH)

    # class Meta:
    #     model = get_invitation_model()
    #     fields = ['email']
    #     pass
