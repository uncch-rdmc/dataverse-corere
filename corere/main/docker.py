import docker, logging, subprocess
from corere.main import git as g
from corere.main import models as m
logger = logging.getLogger(__name__)

def hello_list():
    client = docker.from_env()
    client.containers.run('r2dhttps-3a-2f-2fgithub-2ecom-2fnorvig-2fpytudesf63b403:latest', detach=True)
    print(client.containers.list())

def build_repo2docker_image(manuscript):
    print(manuscript.get_max_submission_version_id())
    try:
        manuscript.manuscript_containerinfo.delete() #for now we just delete it each time
    except Exception as e: #TODO: make more specific
        print("EXCEPTION ", e)
        pass 

    path = g.get_submission_repo_path(manuscript)
    result = subprocess.run(["jupyter-repo2docker " + path + " --no-run --json-logs --image-name " + ""], shell=True, capture_output=True)
    container_info = m.ContainerInfo()
    container_info.image_id = "blah"
    container_info.submission_version = 99
    container_info.manuscript = manuscript
    container_info.save()

    print(result.stdout)
    print(result.stderr)

def start_repo2docker_container(manuscript):
    pass

#Run Command
# docker run -p 54321:8888 12c7e0b2e62f jupyter notebook --ip 0.0.0.0 --NotebookApp.custom_display_url=http://0.0.0.0:54321

#What are the steps:
# - Build Image
# - Run image as a container
#   - Eventually will need to handle the OAuth2-Proxy crap
# - Delete Container
# - Delete Image