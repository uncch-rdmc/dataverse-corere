from django.contrib import admin
from corere.apps.wholetale import models as wtm

# Register your models here.
admin.site.register(wtm.Tale)
admin.site.register(wtm.TaleVersion)
admin.site.register(wtm.TaleImageChoice)