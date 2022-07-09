import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError
from corere.main import constants as c
from corere.main import wholetale_corere as w
from corere.apps.wholetale import models as wtm
from corere.main import models as m

# from corere.main.models import User
# from django.contrib.auth.models import Group

# TODO: Maybe move over the the WholeTale app?
class Command(BaseCommand):
    help = "Pulls info from Whole Tale to populate system models. Currently only used to populate WholeTale image choices."

    def handle(self, *args, **options):
        print("Pulling images from Whole Tale")
        print("")
        images = w.WholeTaleCorere(admin=True).get_images()  # this will error out if no connection, which is fine as an admin command

        new_env_choices = []
        existing_env_choices = []
        for image in images:
            try:
                wtm.ImageChoice.objects.create(wt_id=image.get("_id"), name=image.get("name"))  # if exists it will be gotten then nothing done with\
                new_env_choices = new_env_choices + [image.get("_id"), image.get("name")]
            except IntegrityError as e:
                if str(e.__cause__).startswith("duplicate key value violates unique constraint"):
                    existing_env_choices = existing_env_choices + [image.get("_id"), image.get("name")]
                else:
                    raise (e)

        print("New images pulled from Whole Tale:")
        print(new_env_choices)
        print("")
        print("Previously existing images pulled from Whole Tale:")
        print(existing_env_choices)
        print("")
        print("Also creating 'Other' option for use in CORE2 forms.")
        wtm.ImageChoice.objects.get_or_create(
            wt_id="Other", name="Other", show_last=True
        )  # this shouldn't conflict because the id is shorter than what wt generates


# If Whole Tale often updates the image (id) for the same named image, we may want to add a check here to identify when we have duplicate named images
