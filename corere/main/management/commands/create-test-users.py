from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from corere.main import constants as c
from corere.main.models import User
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Create a test user for each of the 4 roles in CoReRe."

    def handle(self, *args, **options):
        if(not (hasattr(settings, 'DEBUG') and settings.DEBUG)):
            print("Test users cannot be created in production")
            return
        else:
            password = input("%s " % "What password do you wish to set for these users?")

            author = User.objects.create_user('TestAuthor', email="TestAuthor@test.com", password=password)
            author.is_staff=True #For login through the admin console. TODO: Delete when auth gets more consistent.
            author.save()
            Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(author)

            editor = User.objects.create_user('TestEditor', email="TestEditor@test.com", password=password)
            editor.is_staff=True #For login through the admin console. TODO: Delete when auth gets more consistent.
            editor.save()
            Group.objects.get(name=c.GROUP_ROLE_EDITOR).user_set.add(editor)

            curator = User.objects.create_user('TestCurator', email="TestCurator@test.com", password=password)
            curator.is_staff=True #For login through the admin console. TODO: Delete when auth gets more consistent.
            curator.save()
            Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(curator)

            verifier = User.objects.create_user('TestVerifier', email="TestVerifier@test.com", password=password)
            verifier.is_staff=True #For login through the admin console. TODO: Delete when auth gets more consistent.
            verifier.save()
            Group.objects.get(name=c.GROUP_ROLE_VERIFIER).user_set.add(verifier)

            print("Users [TestAuthor, TestEditor, TestCurator, TestVerifier] have been created")


