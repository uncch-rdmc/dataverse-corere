import requests
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from corere.main import constants as c
from corere.main import wholetale_corere as w
from corere.apps.wholetale import models as wtm
from corere.main import models as m
# from corere.main.models import User
# from django.contrib.auth.models import Group

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
                if(wtc_group['name'].startswith(GROUP_MANUSCRIPT_AUTHOR_PREFIX) or wtc_group['name'].startswith(GROUP_MANUSCRIPT_EDITOR_PREFIX)
                or wtc_group['name'].startswith(GROUP_MANUSCRIPT_CURATOR_PREFIX) or wtc_group['name'].startswith(GROUP_MANUSCRIPT_VERIFIER_PREFIX)
                or wtc_group['name'].startswith(GROUP_MANUSCRIPT_ADMIN_PREFIX)):
                    wtc.delete_group(wtc_group["_id"])
                    print(f"Group '{wtc_group['name']}' deleted")

            wtm.GroupConnector.objects.all().delete()
            print("All Whole Tale instance groups and wholetale.Group deleted.")

        try:
            wtm_group = wtm.GroupConnector.objects.get(is_admins=True)
            wtc_group = wtc.get_group(group_id=wtm_group.wt_id) #NOTE: I changed this from id to wt_id, I think that's right
        except wtm.GroupConnector.DoesNotExist:
            wtm_group = None
            wtc_group = None
            pass
        
        #Note: We create this admin group in WT but don't use it currently
        if not wtc_group:
            wtc_group = wtc.create_group(name=c.GROUP_MANUSCRIPT_ADMIN)
            print("Whole Tale instance group did not exist and was created")

        if createlocal:
            if wtm_group:
                print("Local wholetale.Group already exists, createlocal skipped.")
            else:
                wtm.GroupConnector.objects.create(is_admins=True, wt_id=wtc_group['_id'])
                print("Local wholetale.Group created")