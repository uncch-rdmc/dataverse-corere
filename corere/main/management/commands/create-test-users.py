from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from corere.main import constants as c
from corere.main.views.users import helper_create_user_and_invite
from corere.main.models import User
from django.contrib.auth.models import Group
from django.http import HttpRequest

class Command(BaseCommand):
    help = "Create a test user for each of the 4 roles in CORE2."

    def add_arguments(self, parser):
        parser.add_argument('--testlocal', action='store_true', help='Creates test users for OAuth login')

        parser.add_argument('-a', '--author', nargs='+', type=str, help='Author email for OAuth login')
        parser.add_argument('-e', '--editor', nargs='+', type=str, help='Editor email for OAuth login')
        parser.add_argument('-c', '--curator', nargs='+', type=str, help='Curator email for OAuth login')
        parser.add_argument('-ve', '--verifier', nargs='+', type=str, help='Verifier email for OAuth login')

    def handle(self, *args, **options):
        testlocal = options.get('testlocal', [])
        authors = options.get('author', [])
        editors = options.get('editor', [])
        curators = options.get('curator', [])
        verifiers = options.get('verifier', [])

        if testlocal:    
            if author or editor or curator or verifier:
                print("Role emails can only be provided for creation of oauth accounts")
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

                print("Users [TestAuthor, TestEditor, TestCurator, TestVerifier] have been created without oauth for local testing")
        else:
            request = HttpRequest()
            request.user = None     
            request.META['SERVER_NAME'], request.META['SERVER_PORT'] = settings.SERVER_ADDRESS.split(":")
            if authors:
                for email in authors:
                    role = Group.objects.get(name=c.GROUP_ROLE_AUTHOR) 
                    helper_create_user_and_invite(request, email, 'Author', 'Test', role)
            if editors:
                for email in editors:
                    role = Group.objects.get(name=c.GROUP_ROLE_EDITOR) 
                    helper_create_user_and_invite(request, email, 'Editor', 'Test', role)
            if curators:
                for email in curators:
                    role = Group.objects.get(name=c.GROUP_ROLE_CURATOR) 
                    helper_create_user_and_invite(request, email, 'Curator', 'Test', role)
            if verifiers:
                for email in verifiers:
                    role = Group.objects.get(name=c.GROUP_ROLE_VERIFIER) 
                    helper_create_user_and_invite(request, email, 'Verifier', 'Test', role)

            print("Users have been created with the designated roles for the provided emails. The users still need to accept the invites via email and set OAuth accesses on first login.")

            



