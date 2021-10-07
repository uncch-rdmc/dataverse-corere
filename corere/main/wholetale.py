import sseclient
from django.conf import settings
from girder_client import GirderClient
from pathlib import Path
import time

#Some code taken from https://github.com/whole-tale/corere-mock

class WholeTale:
    class InstanceStatus:
        LAUNCHING = 0
        RUNNING = 1
        ERROR = 2

    def __init__(self):
        self.gc = GirderClient(apiUrl="https://girder."+settings.WHOLETALE_BASE_URL+"/api/v1")
        self.gc.authenticate(apiKey=settings.WHOLETALE_ADMIN_GIRDER_API_KEY)
        # self.tale = self.create_tale()
        # self.sse_handler = threading.Thread(
        #     target=event_listener, args=(self.gc,), daemon=False
        # )
        # self.sse_handler.start()

    #This should be run on submission start before uploading files
    #We create a new tale for each submission for access control reasons.
    #The alternative would be to create a version for each submission, there is not version-level access control.
    def create_tale(self, title, image_id):
        #image = self.gc.get("/image", parameters={"text": image_name})
#        print(image)
#        print(image[0].get("_id"))
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

    def run(self, tale_id):
        # if submissionId is not None:
        #     print("We would revert to that version. Pass now")
        print("RUN")
        tale = self.gc.get(f"/tale/{tale_id}")
        instance = self.gc.post("/instance", parameters={"taleId": tale["_id"]})
        print(instance)
        while instance["status"] == self.InstanceStatus.LAUNCHING:
            time.sleep(2)
            instance = self.gc.get(f"/instance/{instance['_id']}")
        return instance

    def stop(self, instance):
        self.gc.delete(f"/instance/{instance['_id']}")

    def download_files(self, path, folder_id=None):
        if folder_id is None:
            folder_id = self.tale["workspaceId"]  # otherwise it should be version

        self.gc.downloadFolderRecursive(folder_id, path)

    def get_images(self):
        return self.gc.get("/image")
