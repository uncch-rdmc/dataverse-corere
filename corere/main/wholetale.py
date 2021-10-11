import time, datetime, sseclient, threading #, json
from django.conf import settings
from girder_client import GirderClient
from pathlib import Path

#Some code taken from https://github.com/whole-tale/corere-mock

class WholeTale:
    class InstanceStatus:
        LAUNCHING = 0
        RUNNING = 1
        ERROR = 2

    def __init__(self):#, event_thread=False):
        self.gc = GirderClient(apiUrl="https://girder."+settings.WHOLETALE_BASE_URL+"/api/v1")
        self.gc.authenticate(apiKey=settings.WHOLETALE_ADMIN_GIRDER_API_KEY)

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

