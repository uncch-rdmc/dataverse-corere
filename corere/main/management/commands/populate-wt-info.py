import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from corere.main import constants as c
from corere.main import wholetale as w
from corere.main import models as m
# from corere.main.models import User
# from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Pulls info from Whole Tale to populate system models. Currently only used to populate WholeTale image choices."

    def handle(self, *args, **options):
        print("Pulling images from Whole Tale")
        images = w.WholeTale().get_images() #this will error out if no connection, which is fine as an admin command
        
        m.TaleImageChoice.objects.all().delete()
        
        wt_compute_env_choices = []
        for image in images:
            m.TaleImageChoice.objects.create(wt_id=image.get('_id'), name=image.get('name'))
            wt_compute_env_choices = wt_compute_env_choices + [image.get('_id'), image.get('name')]

        print("Images pulled from Whole Tale:")
        print(wt_compute_env_choices)