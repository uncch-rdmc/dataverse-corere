import time, datetime, sseclient, threading #, json
from django.conf import settings
from girder_client import GirderClient
from pathlib import Path

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

            #After connecting as a user (via token) we check that there are any corere invitations and accept them if so
            #TODO: Does this mean we need to add a custom string for corere names?
            #TODO: Does our group name implementation mean that if multiple installations use the same WT it'll blow up?


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
    
    #TODO: I'm unsure whether this is the actual format users come in as from WT
    #TODO: This doesn't pre-check to see if the acl already exists
    #TODO: I was advised to not actually use the -1 level, instead just remove acl. I should add a flag for that?
    #TODO: It looks like if a tale has running instances we cannot update the access. 
    #TODO: change this code to not require an actual WT user/group?
    #TODO: I need to be able to associate our users with WT users. What does that connect on??
    def set_access(self, tale_id, level, user=None, group=None, remove_on_none=True):
        #New strat: 
        #   - get ACLs for a tale
        #   - check if user/group already exists in ACLs
        #       - If so, update existing ACL with new level
        #       - Else, set new ACL     
        #   - If remove_on_none and level is -1 (NONE), pop ACL out
        
        acls = get_access(tale_id)

        if user and group:
            #TODO: Error
            pass

        #TODO-WT: I'm ignoring users for now as we're doing everything in groups. But do this ASAP!
        if user:
            new_acl = {
                'login': user['login'],
                'level': level,
                'id': str(user['_id']),
                'flags': [],
                'name': '%s %s' % (
                    user['firstName'], user['lastName']
                )
            }

            acls['users'].append(new_acl)

        elif group:

            new_acl = {
                'id': group['_id'],
                'name': group['name'],
                'flags': [],
                'level': level
            }

            acls['groups'].append(new_acl)

        else:
            #TODO: Error
            pass

        print(acls)
        self.gc.put("/tale/{}/access".format(tale_id),
            parameters={'access': json.dumps(acls)})
    
    def create_group(self, name, public=False):
        return self.gc.post("/group", parameters={"name": name, "public": public})

    def get_group(self, name, exact=True):
        return self.gc.get("/group", parameters={"text": name, "exact": exact})

    def delete_group(name):
        group = get_group(name)
        if groups:
            self.gc.delete("/group/{}".format(groups[0]["_id"]))
        else:
            pass
            #TODO: ERROR

    #These two group functions will be called at the same time for corere. 
    #They are kept separate as the invite will be called as the group admin, while the accept will be called as the user

    def invite_user_to_group(user_id, group_name):
        group = get_group(group_name)
        if groups:
            self.gc.post("group/{}/invitation".format(groups[0]["_id"]), parameters={"level": AccessType.READ, "quiet": True},
                data={"userId": user_id})

    def accept_group_invite(group_name):
        group = get_group(group_name)
        if groups:
            self.gc.post("group/{}/member".format(groups[0]["_id"]))


    # def delete_user(user_info):
    #     users = gc.get("/user", parameters={"text": user_info["login"]})
    #     if users:
    #         gc.delete("/user/{}".format(users[0]["_id"]))


