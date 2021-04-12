from django.core.management.base import BaseCommand, CommandError
#from django.conf import settings
#from corere.main import constants as c
from corere.main import models as m
from corere.main import docker as d
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Wipe docker stack for a Manuscript (jupyter-notebook, oauthproxy, network), along with its ContainerInfo."

    def add_arguments(self, parser):
        parser.add_argument('manuscript_id', type=int)

    def handle(self, *args, **options):
        manuscript = m.Manuscript.objects.get(id=options['manuscript_id'])

        if input("Are you sure you wish to delete the docker stack for 'Manuscript " + str(manuscript.id) + " - " + manuscript.title + "'? (y/n)") != "y":
            exit() 

        return d.delete_manuscript_docker_stack(manuscript, remove_container_info=True)