from django.forms import ModelForm
from .models import Manuscript
class ManuscriptForm(ModelForm):
    class Meta:
        model = Manuscript
        fields = ['title','note_text','doi','open_data','status']