from django.core.management.base import BaseCommand, CommandError
#from django.conf import settings
#from corere.main import constants as c
from corere.main import models as m
from corere.main import docker as d
from django.contrib.auth.models import Group

#TODO: If we run into many issues with intermediate failures that end uncleanly, we should probably delete all the resources by tag
#      This will require improving the tags somewhat, including the manuscript id
class Command(BaseCommand):
    help = "Wipe docker stack for a Manuscript (jupyter-notebook, oauthproxy, network), along with its ContainerInfo. Note that this actually prunes all networks, as deleting multiple networks by name does not work."

    def add_arguments(self, parser):
        parser.add_argument('manuscript_id', type=int)
        parser.add_argument('--crude', action='store_true', help='Runs the crude deletion, which does not require an intact ContainerInfo and stack. The only downside to this is currently if you delete the last containers via this method, the creation of your first containers is very slow.')

    def handle(self, *args, **options):
        manuscript = m.Manuscript.objects.get(id=options['manuscript_id'])

        if input("Are you sure you wish to delete the docker stack for Manuscript " + manuscript. get_display_name + "? (y/n)") != "y":
            exit() 

        crude = options.get('crude', [])

        if(crude):
            return d.delete_manuscript_docker_stack_crude(manuscript)
        else:
            return d.delete_manuscript_docker_stack(manuscript)