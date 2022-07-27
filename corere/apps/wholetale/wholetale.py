import time, datetime, sseclient, threading, json, requests, random, string, logging
from django.conf import settings
from girder_client import GirderClient
from pathlib import Path
from corere.apps.wholetale import models as wtm

logger = logging.getLogger(__name__)

# Some code taken from https://github.com/whole-tale/corere-mock
# Some code also taken from https://gist.github.com/craig-willis/1d928c9afe78ff2a55a804c35637fa42


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

    def __init__(self, token=None, admin=False):  # , event_thread=False):
        self.gc = GirderClient(
            apiUrl="https://girder." + settings.WHOLETALE_BASE_URL + "/api/v1"
        )  # If you change this string, also look at middleware.py
        if admin:
            if token:
                raise ValueError("Token and admin cannot be provided at the same time")
            self.gc.authenticate(apiKey=settings.WHOLETALE_ADMIN_GIRDER_API_KEY)
        elif token:
            self.gc.setToken(token)
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

    # This should be run on submission start before uploading files
    # We create a new tale for each submission for access control reasons.
    # The alternative would be to create a version for each submission, there is not version-level access control.
    # NOTE: This command assumes your corere server is running as https because if it isn't the csp setting won't work anyways
    def create_tale(self, title, image_id):
        # TODO-WT: We should only be setting the config if the tale is a jupyternotebook. But this would require which Images are jupyter. This doesn't break anything so for now it'll stay.
        json_dict = {"title": title, "imageId": image_id, "dataSet": []}
        json_dict["config"] = {"csp": f"frame-ancestors 'self' https://dashboard.{settings.WHOLETALE_BASE_URL} https://{settings.SERVER_ADDRESS}"}
        return self.gc.post("/tale", json=json_dict)

    def copy_tale(self, tale_id, new_title=None):
        new_tale_json = self.gc.post(f"/tale/{tale_id}/copy")
        if new_title:
            # title_json = {'title': new_title}
            new_tale_json["title"] = new_title
            new_tale_json = self.update_tale(new_tale_json["_id"], new_tale_json)
        return new_tale_json

    # replace the existing tales fields with the new fields
    def update_tale(self, tale_id, new_tale_json):
        return self.gc.put(f"/tale/{tale_id}", json=new_tale_json)

    # Force deletes the instances of the tale
    def delete_tale(self, tale_id, force=True):
        return self.gc.delete(f"/tale/{tale_id}", parameters={"force": force})

    def create_tale_version(self, tale_id, name, force=True):
        return self.gc.post("/version", parameters={"taleId": tale_id, "name": name, "force": force})

    # May be unused
    def get_tale_version(self, version_id):
        return self.gc.get(f"/version/{version_id}")

    def list_tale_version(self, tale_id):
        return self.gc.get("/version", parameters={"taleId": tale_id, "limit": 10000})

    def get_tale_version(self, tale_id, version_name):
        versions = self.list_tale_version(tale_id)
        for version in versions:
            if version["name"] == version_name:
                return version

    def restore_tale_to_version(self, tale_id, version_id):
        return self.gc.put(f"/tale/{tale_id}/restore", parameters={"versionId": version_id})

    # TODO-WT: We should switch upload_files and delete_tale_files to take the tale itself instead of the tale id, and stop querying it in both as they are called at the same time.

    def upload_files(self, tale_id, str_path):
        """
        path needs to point to a directory with submission files
        """
        tale = self.gc.get(f"/tale/{tale_id}")

        # By default the "*" match ignores hidden folders (e.g. our .git folder)
        glob_path = str_path + "*"
        return self.gc.upload(glob_path, tale["workspaceId"])

    def delete_tale_files(self, tale_id):
        """
        deletes the contents of a folder. Can be used to delete all files in a tale
        """

        tale = self.gc.get(f"/tale/{tale_id}")
        return self.gc.delete(f"/folder/{tale['workspaceId']}/contents")

    # Note: Run will launch a container for the user authenticated.
    def create_instance(self, tale_id, wait_for_complete=False):
        tale = self.gc.get(f"/tale/{tale_id}")
        instance = self.gc.post("/instance", parameters={"taleId": tale["_id"]})

        if wait_for_complete:
            while instance["status"] == self.InstanceStatus.LAUNCHING:
                time.sleep(2)
                instance = get_instance(instance["_id"])

        return instance

    def get_instance(self, instance_id):
        instance = self.gc.get(f"/instance/{instance_id}")
        return instance

    def delete_instance(self, instance_id):
        return self.gc.delete(f"/instance/{instance_id}")

    def download_tale(self, tale_id):
        tale = self.gc.get(f"/tale/{tale_id}")
        return self.download_folder_zip(tale["workspaceId"])

    def download_folder_zip(self, folder_id, mimeFilter=None):
        return self.gc.get(f"/folder/{folder_id}/download", jsonResp=False)  # , parameters={"mimeFilter": mimeFilter})

    # def download_files(self, path, folder_id):
    #     if folder_id is None:
    #         folder_id = self.tale["workspaceId"]  # otherwise it should be version

    #     return self.gc.downloadFolderRecursive(folder_id, path)

    def get_images(self):
        return self.gc.get("/image")

    def get_logged_in_user(self):
        return self.gc.get("/user/me")

    def get_access(self, tale_id):
        return self.gc.get("/tale/{}/access".format(tale_id))

    def create_group(self, name, public=False):
        return self.gc.post("/group", parameters={"name": name, "public": public})

    def create_group_with_hash(self, name):
        """create a group with a random string attached to the end, to practically avoid collisions"""
        our_hash = random.choices(string.ascii_uppercase + string.digits, k=64)
        return self.create_group(name + " " + "".join(our_hash))

    def get_group(self, group_id):
        return self.gc.get("/group/{}".format(group_id))

    def get_all_groups(self):
        return self.gc.get("/group", parameters={"limit": 10000})

    def delete_group(self, group_id):
        self.gc.delete("/group/{}".format(group_id))

    # invite and accept will be called at the same time for corere.
    # They are kept separate as the invite will be called as the group admin, while the accept will be called as the user
    def invite_user_to_group(self, user_id, group_id):
        try:
            self.gc.post("group/{}/invitation".format(group_id), parameters={"level": self.AccessType.READ, "quiet": True}, data={"userId": user_id})
        except requests.HTTPError as e:
            if e.response.status_code == 400 and json.loads(e.responseText)["message"] == "User is already in this group.":
                logger.warning(f"Whole tale user {user_id} was added to group {group_id}, of which they were already a member.")
                return
            raise e

    def accept_group_invite(self, group_id):
        self.gc.post("group/{}/member".format(group_id))

    # NOTE: This works on invitations as well.
    def remove_user_from_group(self, user_id, group_id):
        # Note: the documentation says formData but using data causes it to error.
        self.gc.delete("group/{}/member".format(group_id), parameters={"userId": user_id})
