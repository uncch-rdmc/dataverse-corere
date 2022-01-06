import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from corere.main import constants as c
from corere.main import wholetale_corere as w
from corere.apps.wholetale import models as wtm
from corere.main import models as m
# from corere.main.models import User
# from django.contrib.auth.models import Group

#TODO-WT: Maybe move over the the WholeTale app?
#NOTE: This code uses 3 types of groups. Local corere groups, Whole Tale remote instance groups (accessed via api), and wholetale.group(s) which store the connetion between the two
class Command(BaseCommand):
    help = "Initializes the state of the connected Whole Tale instance. Currently this means creating the admin group on the Whole Tale server."

    def add_arguments(self, parser):
        parser.add_argument('--createlocal', action='store_true', help='Create the local wholetale.admin group connected to what is created in the Whole Tale instance.')
        parser.add_argument('--deleteall', action='store_true', help='Deletes all remote/local groups (and tales someday?).')
        ## TODO: Enable this and write its code
        # parser.add_argument('--clear', action='store_true', help='Deletes all tales owned by the admin user.')

    def handle(self, *args, **options):
        wtc = w.WholeTaleCorere(admin=True)

        createlocal = options.get('createlocal', [])
        deleteall = options.get('deleteall', [])

        if deleteall:
            for wtc_group in wtc.get_all_groups():
                #TODO-WT: This should probably check if the groups start with our managed prefixes?
                #TODO-WT: I probably need to better document re-launching for testing purposes
                #TODO-WT: 
                wtc.delete_group(wtc_group["_id"])
                print(f"Group '{wtc_group['name']}' deleted")

            wtm.GroupConnector.objects.all().delete()
            print("All Whole Tale instance groups and wholetale.Group deleted.")

# TODO-WT: Should there be one admin group for the whole project, or one per manuscript
# One per project may be simpler on the WT side, but one per manuscript may be easier for our logic??
# That being said, admin access in corere is not per manuscript...

        try:
            wtm_group = wtm.GroupConnector.objects.get(is_admins=True)
            wtc_group = wtc.get_group(group_id=wtm_group.wt_id) #NOTE: I changed this from id to wt_id, I think that's right
        except wtm.GroupConnector.DoesNotExist:
            wtm_group = None
            wtc_group = None
            pass
        
        if not wtc_group:
            wtc_group = wtc.create_group(name=c.GROUP_MANUSCRIPT_ADMIN)
            print("Whole Tale instance group did not exist and was created")

        if createlocal:
            if wtm_group:
                print("Local wholetale.Group already exists, createlocal skipped.")
            else:
                wtm.GroupConnector.objects.create(is_admins=True, wt_id=wtc_group['_id'])
                print("Local wholetale.Group created")