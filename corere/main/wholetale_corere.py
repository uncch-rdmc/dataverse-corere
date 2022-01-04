import requests, json
from corere.apps.wholetale import models as wtm
from corere.apps.wholetale.wholetale import WholeTale
from corere.main import models as m
from corere.main import constants as c
from django.db.models import Q  
from django.conf import settings

#We create a subclass of WholeTale to add the corere-specific code.
#This is so the WholeTale code can be better reused by others in the future
class WholeTaleCorere(WholeTale):
    # Attempts to create a Whole Tale instance. If there is no space, the code attempts to remove other instances for the user that are owned by CORE2.
    # If this fails, the system tells the user to clean it up themselves in Whole Tale
    # NOTE: This code looks at the object model to tell what instances exist. So if somehow a CORE2 WT instance is created that isn't stored in our database, the system won't clean it up.
    def create_instance_with_purge(self, tale, user):
        try:
            return self.create_instance(tale.tale_id)
        except requests.HTTPError as e:
            print(e.__dict__)
            print(json.loads(e.responseText)['message'])
            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                #Delete instances on other manuscript for the user
                
                #other_manuscript_instances = user.user_instances.objects.filter(~Q(tale__manuscript==tale.manuscript))
                other_manuscript_instances = wtm.Instance.objects.filter(Q(corere_user=user) & ~Q(tale__manuscript=tale.manuscript))

                for oi in other_manuscript_instances:
                    self.delete_instance(oi.instance_id)
                    oi.delete()
                try:
                    return self.create_instance(tale.tale_id)
                except requests.HTTPError as e:
                    if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                        #Delete the farthest back submission-instance on the same manuscript for the user
                        #other_submission_instances = user.user_instances.objects.filter(Q(tale__manuscript==tale.manuscript) & ~Q(tale__submission==tale.submission))
                        other_submission_instances = wtm.Instance.objects.filter(Q(corere_user=user) & Q(tale__manuscript=tale.manuscript) & ~Q(tale__submission=tale.submission))

                        #This case should only happen if you have two older instances on this manuscript
                        if(other_submission_instances.count() > 1):
                            farthest_back_submission_instance = other_submission_instances.order_by(tale__submission__version_id).first()
                            self.delete_instance(farthest_back_submission_instance.instance_id)
                            farthest_back_submission_instance.delete()
                        else:
                            raise Exception(f'Your maximum number of instances in Whole Tale has been reached. Some of your running instances are not managed by CORE2 so they cannot be deleted. Please go to {settings.WHOLETALE_BASE_URL} and delete running instances manually before proceeding.')
                        try:
                            return self.create_instance(tale.tale_id)
                        except requests.HTTPError as e:
                            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                                raise Exception(f'Your maximum number of instances in Whole Tale has been reached. Some of your running instances are not managed by CORE2 so they cannot be deleted. Please go to {settings.WHOLETALE_BASE_URL} and delete running instances manually before proceeding.')

#TODO-WT: This is wrong no? We want to use the manuscript id????
def get_wt_group_name(group_prefix, manuscript):
    return c.generate_group_name(group_prefix, manuscript)

#This is nessecary as users can have multiple groups. Admins are the primary example.
#Current return hierarchy: author > curator > verifier > editor
#TODO-WT: Should we be launching containers also as the admin group???
def get_dominant_group_connector(user, submission):
    user_groups = user.groups.all()
    
    if corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX, submission.manuscript)).first():
        print("AUTHOR")
        pass
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_CURATOR_PREFIX, submission.manuscript)).first():
        print("CURATOR")
        pass 
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX, submission.manuscript)).first():
        print("VERIFIER")
        pass 
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_EDITOR_PREFIX, submission.manuscript)).first():
        print("EDITOR")
        pass 

    return wtm.GroupConnector.objects.get(corere_group=corere_group)

def get_model_instance(user, submission):
    group_connector = get_dominant_group_connector(user, submission)
    print(group_connector.__dict__)
    return group_connector.groupconnector_tales.get(submission=submission).tale_instances.filter(corere_user=user).first()