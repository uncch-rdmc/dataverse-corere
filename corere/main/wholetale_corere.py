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
    def __init__(self, token=None, admin=False):
        super(WholeTaleCorere, self).__init__(token, admin)
        if token:
            #When connecting as a user, we check that there are any wt-group invitations owned by corere, and accept them if so
            wt_user = self.gc.get("/user/me")
            for invite in wt_user['groupInvites']:
                if(wtm.GroupConnector.objects.filter(wt_id=invite['groupId']).exists()): #if group is a corere group
                    self.gc.post("group/{}/member".format(invite['groupId'])) #accept invite

    # Attempts to create a Whole Tale instance. If there is no space, the code attempts to remove other instances for the user that are owned by CORE2.
    # If this fails, the system tells the user to clean it up themselves in Whole Tale
    # NOTE: This code looks at the object model to tell what instances exist. So if somehow a CORE2 WT instance is created that isn't stored in our database, the system won't clean it up.
    def create_instance_with_purge(self, tale, user):
        try:
            return self.create_instance(tale.wt_id)
        except requests.HTTPError as e:
            print(e.__dict__)
            print(json.loads(e.responseText)['message'])
            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                #Delete instances on other manuscript for the user
                
                #other_manuscript_instances = user.user_instances.objects.filter(~Q(tale__manuscript==tale.manuscript))
                other_manuscript_instances = wtm.Instance.objects.filter(Q(corere_user=user) & ~Q(tale__manuscript=tale.manuscript))

                for oi in other_manuscript_instances:
                    self.delete_instance(oi.wt_id)
                    oi.delete()
                try:
                    return self.create_instance(tale.wt_id)
                except requests.HTTPError as e:
                    if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                        #Delete the farthest back submission-instance on the same manuscript for the user
                        #other_submission_instances = user.user_instances.objects.filter(Q(tale__manuscript==tale.manuscript) & ~Q(tale__submission==tale.submission))
                        other_submission_instances = wtm.Instance.objects.filter(Q(corere_user=user) & Q(tale__manuscript=tale.manuscript) & ~Q(tale__submission=tale.submission))

                        #This case should only happen if you have two older instances on this manuscript
                        if(other_submission_instances.count() > 1):
                            farthest_back_submission_instance = other_submission_instances.order_by(tale__submission__version_id).first()
                            self.delete_instance(farthest_back_submission_instance.wt_id)
                            farthest_back_submission_instance.delete()
                        else:
                            raise Exception(f'Your maximum number of instances in Whole Tale has been reached. Some of your running instances are not managed by CORE2 so they cannot be deleted. Please go to {settings.WHOLETALE_BASE_URL} and delete running instances manually before proceeding.')
                        try:
                            return self.create_instance(tale.wt_id)
                        except requests.HTTPError as e:
                            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                                raise Exception(f'Your maximum number of instances in Whole Tale has been reached. Some of your running instances are not managed by CORE2 so they cannot be deleted. Please go to {settings.WHOLETALE_BASE_URL} and delete running instances manually before proceeding.')

    def set_group_access(self, tale_id, level, wtm_group, force_instance_shutdown=True):
        acls = self.gc.get("/tale/{}/access".format(tale_id))

        existing_index = next((i for i, item in enumerate(acls['groups']) if item["id"] == wtm_group.wt_id), None)
        if existing_index:
            acls['groups'].pop(existing_index) #we remove the old, never to be seen again

        if(level != self.AccessType.NONE): #If access is none, we need to not add it, instead of setting level as NONE (-1)
            acl = {
                'id': wtm_group.wt_id,
                'name': wtm_group.corere_group.name,
                'flags': [],
                'level': level
            }

            acls['groups'].append(acl)    

        self.gc.put("/tale/{}/access".format(tale_id), parameters={'access': json.dumps(acls), 'force': force_instance_shutdown})

def get_wt_group_name(group_prefix, manuscript):
    return c.generate_group_name(group_prefix, manuscript)

def get_tale_version_name(version_id):
    return f"Submission {version_id}"

#This is nessecary as users can have multiple groups. Admins are the primary example.
#Current return hierarchy: author > curator > verifier > editor
#We do not treat admin in a special way at this point
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