import docker, logging, subprocess, random
from django.conf import settings
from corere.main import git as g
from corere.main import models as m
from django.db.models import Q
logger = logging.getLogger(__name__)

# def hello_list():
#     client = docker.from_env()
#     client.containers.run('r2dhttps-3a-2f-2fgithub-2ecom-2fnorvig-2fpytudesf63b403:latest', detach=True)
#     print(client.containers.list())

#TODO: Better error checking. stderr has concents even when its successful.
def build_repo2docker_image(manuscript):
    try:
        manuscript.manuscript_containerinfo.delete() #for now we just delete it each time
        #TODO: Delete oauth2 proxy as well
    except Exception as e: #TODO: make more specific
        print("EXCEPTION ", e)
        pass 

    path = g.get_submission_repo_path(manuscript)
    sub_version = manuscript.get_max_submission_version_id()
    image_name = (str(manuscript.id) + "-" + manuscript.slug + "-version" + str(sub_version))[:128] + ":" + settings.DOCKER_GEN_TAG  
    #jupyter-repo2docker  --no-run --image-name "test-version1:corere-jupyter" "../../../corere-git/10_-_manuscript_-_test10"
    run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"
    result = subprocess.run([run_string], shell=True, capture_output=True)
    
    container_info = m.ContainerInfo()
    container_info.repo_image_name = image_name
    container_info.submission_version = sub_version
    container_info.manuscript = manuscript
    container_info.save()

    #TODO: better logging, make sure there is nothing compromising in the logs
    #print(result.stderr)
    #print(result.stdout)

def start_repo2docker_container(manuscript):
    while True:
        container_port = random.randint(50000, 50019)
        if not m.ContainerInfo.objects.filter(Q(repo_container_port=container_port) | Q(proxy_container_port=container_port)).exists():
            break

    container_ip = "0.0.0.0"
    client = docker.from_env()
    container_info = manuscript.manuscript_containerinfo
    #print(container_info.image_name)
    run_string = "jupyter notebook --ip " + container_ip + " --NotebookApp.token='' --NotebookApp.password='' " #--NotebookApp.allow_origin='*'
    #TODO: Set the "*" to be more specific
    run_string += "--NotebookApp.tornado_settings=\"{ 'headers': { 'Content-Security-Policy': \\\"frame-ancestors 'self' *\\\" } }\""

    container = client.containers.run(container_info.repo_image_name, run_string, ports={'8888/tcp': container_port},detach=True)

    container_info.repo_container_port = container_port
    container_info.repo_container_ip = container_ip
    container_info.save()
    print(container_info.__dict__)

    #return container_info.container_public_address()


def start_oauthproxy_container(manuscript):
    #TODO: Delete existing proxy. I should also do the same thing for start_repo2docker_container

    while True:
        container_port = random.randint(50020, 50039)
        if not m.ContainerInfo.objects.filter(Q(repo_container_port=container_port) | Q(proxy_container_port=container_port)).exists():
            break

    run_string = ""

    container_ip = "localhost"
    client = docker.from_env()
    container_info = manuscript.manuscript_containerinfo

    container_info.proxy_container_port = container_port
    container_info.proxy_container_ip = container_ip
    container_info.save()

    #TODO: Should actually use a config file and just do the "changing" parameters like this
    #TODO: Replace 0.0.0.0s with correct variables. Also probably other things
    #"'" +container_info.proxy_container_ip+":"+str(container_info.proxy_container_port)+ "'" + " " \

    repo_container_ip = container_info.repo_container_ip
    if(repo_container_ip == "0.0.0.0"):
        repo_container_ip = "localhost"
    #For some reason, globus does not like a url that ends in a port for the redirect url, hence why we point to "/tree". May be user error on my end.

    command = "--http-address=" + "'0.0.0.0:4180'" + " " \
            + "--https-address=" + "':443'" + " " \
            + "--redirect-url=" + "'http://"+repo_container_ip+":"+str(container_info.repo_container_port) + "/tree' " \
            + "--upstream=" + "'http://0.0.0.0:54329/'" + " " \
            + "--email-domain=" + "'*'" + " " \
            + "--provider=" + "'oidc'" + " " \
            + "--provider-display-name=" + "'Globus'" + " " \
            + "--oidc-issuer-url=" + "'https://auth.globus.org'" + " " \
            + "--client-id=" + "'54171f39-1251-40b7-ab06-78a43c267650'" + " " \
            + "--client-secret=" + "'ya9okC55lOXmAp3LqZ2biJcWhu6k2MbAQnImJstHqB0='" + " " \
            + "--cookie-name=" + "'_oauth2_proxy'" + " " \
            + "--cookie-secret=" + "'3BC2D1B35884E2CCF5F964775FB7B74A'" + " " \
            + "--cookie-domain=" + "''" + " " \
            + "--cookie-expire=" + "'5s'" + " " \
            + "--cookie-refresh=" + "'0s'" + " " \
            + "--cookie-secure=" + "'true'" + " " \
            + "--cookie-httponly=" + "'true'" + " " 
    
    print("OAUTH PROXY COMMAND: " + command)

    #for some reason after my changes yesterday running is now broken?
    container = client.containers.run(settings.DOCKER_OAUTH_PROXY_IMAGE, command, ports={'4180/tcp': container_port}, detach=True)
    
    # container_info.proxy_container_port = container_port
    # container_info.proxy_container_ip = container_ip
    # container_info.save()

    #TODO: bad bad bad delete
    import time
    time.sleep(2)
    print(container.logs()) #I'll need to find a way to stream these logs into a django log


    return container_info.container_public_address()
    

#What are the steps:
# - Build Image
# - Run image as a container
#   - Eventually will need to handle the OAuth2-Proxy crap
# - Delete Container
# - Delete Image

#Thoughts:
# - how will I actually do port/ip in production???

# docker run -p 54321:8888 12c7e0b2e62f jupyter notebook --ip 0.0.0.0 --NotebookApp.custom_display_url=http://0.0.0.0:54321


# docker run -p 61111:8888 bitnami/oauth2-proxy:latest oauth2-proxy --http-address='127.0.0.1:4180' --https-address=':443' --redirect-url='http://127.0.0.1:4180' --upstream='http://0.0.0.0:54329/' --email-domain='*' --client-id='54171f39-1251-40b7-ab06-78a43c267650' --client-secret='ya9okC55lOXmAp3LqZ2biJcWhu6k2MbAQnImJstHqB0=' --cookie-name='_oauth2_proxy' --cookie-secret='3BC2D1B35884E2CCF5F964775FB7B74A' --cookie-domain='' --cookie-expire='5s' --cookie-refresh='0s' --cookie-secure='true' --cookie-httponly='true'