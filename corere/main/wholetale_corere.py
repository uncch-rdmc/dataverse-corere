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
    def create_instance_with_purge(self, wtm_tale, user):
        try:
            return self.create_instance(wtm_tale.wt_id)
        except requests.HTTPError as e:
            print("PURGE 1")
            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                print("PURGE 2A")
                #Delete instances on other manuscript for the user. Also cleans up orphan wtm instances it runs into along the way (not all).
                #NOTE: if the user is full from another manuscript's instances, this will delete all (2) of them. We could improve this but this is a bit simpler.
                
                #other_manuscript_instances = user.user_instances.objects.filter(~Q(tale__manuscript==wtm_tale.manuscript))
                other_manuscript_instances = wtm.Instance.objects.filter(Q(corere_user=user) & ~Q(tale__manuscript=wtm_tale.manuscript))
                print("PURGE 2B")
                for wtm_oi in other_manuscript_instances:
                    print("PURGE 2CA")
                    print(f'delete_or_clean other_manuscript submission_id {wtm_oi.tale.submission.id}')
                    delete_success = self.delete_instance_or_nothing(wtm_oi)
                    print("PURGE 2CB")
                    wtm_oi.delete()
                    print("PURGE 2CC")
                    if delete_success: #once we delete one, break
                        print("PURGE 2CD")
                        break
                    print("PURGE 2CZ")  
                try:
                    print("PURGE 2D")
                    return self.create_instance(wtm_tale.wt_id)
                except requests.HTTPError as e:
                    print("PURGE 3")
                    if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                        #Delete the farthest back submission-instance on the same manuscript for the user
                        #other_submission_instances = user.user_instances.objects.filter(Q(tale__manuscript==wtm_tale.manuscript) & ~Q(tale__submission==wtm_tale.submission))
                        other_submission_instances = wtm.Instance.objects.filter(Q(corere_user=user) & Q(tale__manuscript=wtm_tale.manuscript) & ~Q(tale__submission=wtm_tale.submission))

                        #This case should only happen if you have two older instances on this manuscript
                        #If we have orphans wtm_instances, this should clean up the ones along the way (not all).
                        #TODO-WT: Confirm this works as expected, as count was called before and I'm not sure if that works right
                        while(other_submission_instances.count() > 1): 
                            print("PURGE 4")
                            farthest_back_submission_instance = other_submission_instances.order_by('tale__submission__version_id').first()
                            self.delete_instance_or_nothing(farthest_back_submission_instance)
                            print(f'delete_or_clean same_manuscript submission_id {farthest_back_submission_instance.tale.submission.id}')
                            farthest_back_submission_instance.delete()
                        try:
                            return self.create_instance(wtm_tale.wt_id)
                        except requests.HTTPError as e:
                            print("PURGE XBA")
                            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("You have reached a limit for running instances"):
                                print("PURGE XBB")
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

    #TODO-WT: Rename these
    def get_instance_or_nothing(self, wtm_instance):
        """Get the instance. If it doesn't exist on the server return nothing instead of erroring out"""
        try:
            return self.get_instance(wtm_instance.wt_id)
        except requests.HTTPError as e:
            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("Invalid"):
                return

    #This was switched to do nothinn instead of clean, because in the case we were cleaning we were calling the call outside anyways regardless of the error.
    #I added a result to be able to tell if we actually successfully deleted one, as we only want to delete one
    def delete_instance_or_nothing(self, wtm_instance):
        """If the wtc_instance for the wtm_instance does not exist on WT, delete the wtm_instance"""
        try:
            self.delete_instance(wtm_instance.wt_id)
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 400 and json.loads(e.responseText)['message'].startswith("Invalid"):
                #print(f"instance {wtm_instance.wt_id} does not exist on WT server (it may have been deleted already by the user). Removing the WT object.")
                #wtm_instance.delete()
                return False

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
        pass
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_CURATOR_PREFIX, submission.manuscript)).first():
        pass 
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX, submission.manuscript)).first():
        pass 
    elif corere_group := user_groups.filter(name=get_wt_group_name(c.GROUP_MANUSCRIPT_EDITOR_PREFIX, submission.manuscript)).first():
        pass 

    return wtm.GroupConnector.objects.get(corere_group=corere_group)

def get_model_instance(user, submission):
    group_connector = get_dominant_group_connector(user, submission)
    print(group_connector.__dict__)
    return group_connector.groupconnector_tales.get(submission=submission).tale_instances.filter(corere_user=user).first()