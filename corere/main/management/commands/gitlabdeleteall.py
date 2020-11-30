from django.core.management.base import BaseCommand, CommandError
from corere.main.gitlab import gitlab_delete_all_projects, gitlab_delete_all_users_besides_root
from django.conf import settings

class Command(BaseCommand):
    help = "Deletes all resources (users/projects) from the GitLab service connected to CoReRe, excluding the root user. You probably don't want to run this in production."

    def handle(self, *args, **options):
        if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
            print("GitLab is disabled in your settings.py, aborted")
            return
        confirmation = input("%s " % "Are you sure you want to delete all resources for the GitLab service connected to this instance of CoReRe? (yes/no)")
        if(confirmation.lower() != "yes"):
            if(confirmation.lower() != "no"):
                print("Invalid input, please enter yes or no.")
            print("Aborting deletion of Gitlab resources.")
            return
        else:
            print("Beginning deletion, this may take a few seconds per project/user.")
            d_repo_count = gitlab_delete_all_projects()
            print("Deleted %i repos from GitLab" % d_repo_count)
            d_user_count = gitlab_delete_all_users_besides_root()
            print("Deleted %i projects from GitLab" % d_user_count)
            
            
        

# class Command(BaseCommand):
#     help = 'Closes the specified poll for voting'

#     def add_arguments(self, parser):
#         parser.add_argument('poll_ids', nargs='+', type=int)

#     def handle(self, *args, **options):
#         for poll_id in options['poll_ids']:
#             try:
#                 poll = Poll.objects.get(pk=poll_id)
#             except Poll.DoesNotExist:
#                 raise CommandError('Poll "%s" does not exist' % poll_id)

#             poll.opened = False
#             poll.save()

#             self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))
