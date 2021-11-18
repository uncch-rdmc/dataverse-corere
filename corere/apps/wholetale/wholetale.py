import time, datetime, sseclient, threading, json, requests
from django.conf import settings
from girder_client import GirderClient
from pathlib import Path
from corere.apps.wholetale import models as wtm

#Some code taken from https://github.com/whole-tale/corere-mock
#Some code also taken from https://gist.github.com/craig-willis/1d928c9afe78ff2a55a804c35637fa42

class WholeTale:
    class InstanceStatus:
        LAUNCHING = 0
        RUNNING = 1
        ERROR = 2

    class AccessType:
        NONE = -1
        READ = 0
        WRITE = 1
        ADMIN = 2

    def __init__(self, token=None, admin=False):#, event_thread=False):
        self.gc = GirderClient(apiUrl="https://girder."+settings.WHOLETALE_BASE_URL+"/api/v1")
        if admin:
            self.gc.authenticate(apiKey=settings.WHOLETALE_ADMIN_GIRDER_API_KEY)
        elif token:
            self.gc.setToken(token)
            #When connecting as a user, we check that there are any wt-group invitations owned by corere, and accept them if so
            wt_user = self.gc.get("/user/me")
            for invite in wt_user['groupInvites']:
                if(wtm.GroupConnector.objects.filter(group_id=invite['groupId']).exists()): #if group is a corere group
                    self.gc.post("group/{}/member".format(invite['groupId'])) #accept invite
        else:
            raise ValueError("A Whole Tale connection must be provided a girder token or run as an admin.")

    def get_event_stream(self):
        stream = self.gc.sendRestRequest(
            "GET",
            "/notification/stream",
            stream=True,
            headers={"Accept": "text/event-stream"},
            jsonResp=False,
            parameters={"since": int(datetime.datetime.now().timestamp())},
        )
        return stream

    #This should be run on submission start before uploading files
    #We create a new tale for each submission for access control reasons.
    #The alternative would be to create a version for each submission, there is not version-level access control.
    def create_tale(self, title, image_id):
        tale = self.gc.post("/tale", json={"title": title, "imageId": image_id, "dataSet": []})
        return tale

    def upload_files(self, tale_id, str_path):
        """
        path needs to point to a directory with submission files
        """
        print(tale_id)
        tale = self.gc.get(f"/tale/{tale_id}")

        #By default the "*" match ignores hidden folders (e.g. our .git folder)
        glob_path = str_path + "*"
        self.gc.upload(glob_path, tale["workspaceId"])

    #TODO: Do we need the completed instance? Probably yes for the url?
    def run(self, tale_id, wait_for_complete=False):
        tale = self.gc.get(f"/tale/{tale_id}")
        instance = self.gc.post("/instance", parameters={"taleId": tale["_id"]})
        
        if(wait_for_complete):
            while instance["status"] == self.InstanceStatus.LAUNCHING:
                time.sleep(2)
                instance = get_instance(instance['_id'])
        
        return instance

    def get_instance(self, instance_id):
        return self.gc.get(f"/instance/{instance_id}")

    def stop(self, instance):
        self.gc.delete(f"/instance/{instance['_id']}")

    def download_files(self, path, folder_id=None):
        if folder_id is None:
            folder_id = self.tale["workspaceId"]  # otherwise it should be version

        self.gc.downloadFolderRecursive(folder_id, path)

    def get_images(self):
        return self.gc.get("/image")

    def get_logged_in_user(self):
        return self.gc.get("/user/me")

    def get_access(self, tale_id):
        return self.gc.get("/tale/{}/access".format(tale_id))
    
    def set_group_access(self, tale_id, level, wtm_group, force_instance_shutdown=True):
        acls = self.gc.get("/tale/{}/access".format(tale_id))

        existing_index = next((i for i, item in enumerate(acls['groups']) if item["id"] == wtm_group.group_id), None)
        if existing_index:
            acls['groups'].pop(existing_index) #we remove the old, never to be seen again

        if(level != self.AccessType.NONE): #If access is none, we need to not add it, instead of setting level as NONE (-1)
            acl = {
                'id': wtm_group.group_id,
                'name': wtm_group.group_name,
                'flags': [],
                'level': level
            }

            acls['groups'].append(acl)    

        self.gc.put("/tale/{}/access".format(tale_id), parameters={'access': json.dumps(acls), 'force': force_instance_shutdown})
    
    def create_group(self, name, public=False):
        return self.gc.post("/group", parameters={"name": name, "public": public})

    # def get_group(self, name, exact=True):
    #     return self.gc.get("/group", parameters={"text": name, "exact": exact})

    def get_group(self, group_id):
        return self.gc.get("/group/{}".format(group_id))

    def get_all_groups(self):
        return self.gc.get("/group", parameters={"limit": 10000})

    def delete_group(self, group_id):
        self.gc.delete("/group/{}".format(group_id))

    #These two group functions will be called at the same time for corere. 
    #They are kept separate as the invite will be called as the group admin, while the accept will be called as the user

    def invite_user_to_group(self, user_id, group_id):
        try:
            self.gc.post("group/{}/invitation".format(group_id), parameters={"level": self.AccessType.READ, "quiet": True},
                data={"userId": user_id})
        except requests.HTTPError as e:
            print(e.__dict__)
            print(json.loads(e.responseText)['message'])
            if e.response.status_code == 400 and json.loads(e.responseText)['message'] == "User is already in this group.":
                logger.warning(f"Whole tale user {user_id} was added to group {group_id}, of which they were already a member.")
                return
            raise e

    #NOTE: This works on invitations as well.
    def remove_user_from_group(self, user_id, group_id):
        #Note: the documentation says formData but using data causes it to error. If this blows up investigate further
        self.gc.delete("group/{}/member".format(group_id), parameters={"userId": user_id}) #data={"userId": user_id})

    def accept_group_invite(self, group_id):
        self.gc.post("group/{}/member".format(group_id))

    # def delete_user(user_info):
    #     users = gc.get("/user", parameters={"text": user_info["login"]})
    #     if users:
    #         gc.delete("/user/{}".format(users[0]["_id"]))


