from django.forms import ModelForm
from .models import Manuscript, User
class ManuscriptForm(ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','note_text','doi','open_data','editors']

    def __init__ (self, *args, **kwargs):
        super(ManuscriptForm, self).__init__(*args, **kwargs)
        self.fields['editors'].queryset = User.objects.filter(is_editor=True)