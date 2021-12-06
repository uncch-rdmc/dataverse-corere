from corere.apps.wholetale import models as wtm
from corere.apps.wholetale.wholetale import WholeTale
from corere.main import models as m
from corere.main import constants as c

#We create a subclass of WholeTale to add the corere-specific code.
#This is so the WholeTale code can be better reused by others in the future
class WholeTaleCorere(WholeTale):

    #TODO-WT: This is wrong no? We want to use the manuscript id????
    def get_wt_group_name(self, group_prefix, manuscript):
        return c.generate_group_name(group_prefix, manuscript)

    #This is nessecary as users can have multiple groups. Admins are the primary example.
    #Current return hierarchy: author > curator > verifier > editor
    #TODO-WT: Should we be launching containers also as the admin group???
    def get_dominant_group_connector(self, user, submission):
        user_groups = user.groups.all()
        
        if corere_group := user_groups.get(name=self.get_wt_group_name(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX, submission.manuscript)):
            pass
        elif corere_group := user_groups.get(name=self.get_wt_group_name(c.GROUP_MANUSCRIPT_CURATOR_PREFIX, submission.manuscript)):
            pass 
        elif corere_group := user_groups.get(name=self.get_wt_group_name(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX, submission.manuscript)):
            pass 
        elif corere_group := user_groups.get(name=self.get_wt_group_name(c.GROUP_MANUSCRIPT_EDITOR_PREFIX, submission.manuscript)):
            pass 

        return wtm.GroupConnector.objects.get(corere_group=corere_group)
   
    def get_model_instance(self, user, submission):
        group_connector = self.get_dominant_group_connector(user, submission)
        #print(group_connector.__dict__)
        return group_connector.groupconnector_tale.tale_instances.get(corere_user=user)