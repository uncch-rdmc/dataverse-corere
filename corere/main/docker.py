import docker, logging, subprocess, random, io, os
from django.conf import settings
from corere.main import git as g
from corere.main import models as m
from corere.main import constants as c
from django.db.models import Q
logger = logging.getLogger(__name__)

#TODO: Better error checking. stderr has concents even when its successful.
def build_repo2docker_image(manuscript):
    # try:
    #     manuscript.manuscript_containerinfo.delete() #for now we just delete it each time
    #     #TODO: Delete oauth2 proxy as well
    # except Exception as e: #TODO: make more specific
    #     print("EXCEPTION ", e)
    #     pass 

    path = g.get_submission_repo_path(manuscript)
    sub_version = manuscript.get_max_submission_version_id()
    image_name = ("jupyter-" + str(manuscript.id) + "-" + manuscript.slug + "-version" + str(sub_version))[:128] + ":" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id) 
    #jupyter-repo2docker  --no-run --image-name "test-version1:corere-jupyter" "../../../corere-git/10_-_manuscript_-_test10"
    run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"
    result = subprocess.run([run_string], shell=True, capture_output=True)
    
    logger.debug("build_repo2docker_image result:" + str(result))

    #TODO: should this logic be moved outside of this function. Is it needed in other places?
    if (not (hasattr(manuscript, 'manuscript_containerinfo'))):
        container_info = m.ContainerInfo() 
    else:
        container_info = manuscript.manuscript_containerinfo
    container_info.repo_image_name = image_name
    container_info.submission_version = sub_version
    container_info.manuscript = manuscript
    container_info.save()

def delete_repo2docker_image(manuscript, remove_container_info=True):
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.repo_image_name, force=True)
    if(remove_container_info):
        container_info.repo_image_name = ""
        container_info.save()

def _write_oauthproxy_email_list_to_working_directory(manuscript):
    container_info = manuscript.manuscript_containerinfo
    client = docker.from_env()    

    #TODO: I need to write a file with the list of emails allowed to access the container to the filesystem where docker can use it to build
    email_file_path = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/authenticated_emails.txt"
    os.makedirs(os.path.dirname(email_file_path), exist_ok=True) #make folder for build context
    email_file = open(email_file_path, 'w')

    #Get the list of emails allowed to access the notebook
    #For now I think I'm just going to get a list of users in the 4 role groups
    user_email_list = m.User.objects.filter(  Q(groups__name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id)) 
                        | Q(groups__name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(manuscript.id)) 
                        | Q(groups__name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id)) 
                        | Q(groups__name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id))
                        #| Q(is_superuser=True) #This seems to return the same use like a ton of times
    ).values('email')

    for ue in user_email_list:
        print(ue.get("email"))
        email_file.write(ue.get("email")+"\n")

    email_file.close()

def build_oauthproxy_image(manuscript):
    container_info = manuscript.manuscript_containerinfo
    client = docker.from_env()    

    _write_oauthproxy_email_list_to_working_directory(manuscript)

    docker_build_folder = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/"
    dockerfile_path = docker_build_folder + "dockerfile"
    docker_string = "FROM " + settings.DOCKER_OAUTH_PROXY_BASE_IMAGE + "\n" \
                  + "COPY authenticated_emails.txt /opt/bitnami/oauth2-proxy/authenticated_emails.txt"
    with open(dockerfile_path, 'w') as f:
        f.write(docker_string)

    #run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"
    container_info.proxy_image_name = ("oauthproxy-" + str(manuscript.id) + "-" + manuscript.slug)[:128] + ":" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id)
    container_info.save()
    run_string = "docker build . -t " + container_info.proxy_image_name
    result = subprocess.run([run_string], shell=True, capture_output=True, cwd=docker_build_folder)

    logger.debug("build_oauthproxy_image result:" + str(result))

    # dockerfile = io.BytesIO(bytes(docker_string.encode()))
    # #this fails right now because the file I am using has to be in my docker folder
    # client.images.build(fileobj=dockerfile) #custom_context=True

    #print("HEY HEY YA")

    #It looks like we may have to create a tar.gz with the dockerfile and our emails: https://github.com/docker/docker-py/issues/974
    #Or maybe I can change the docker root dir to something that actually exists? https://unix.stackexchange.com/questions/452368/change-docker-root-dir-on-red-hat-linux
    #Or maybe there is some command I can do to get the file I want into docker? https://stackoverflow.com/questions/37789984/how-to-copy-folders-to-docker-image-from-dockerfile
    #I could also just run the build command directly on the filesystem, not through the api, and provide the context https://www.cloudbees.com/blog/3-different-ways-to-provide-docker-build-context/
    #I'm leaning towards using subprocess.run and just running inside a folder in tmp

    #dockerfile.close()

def delete_oauth2proxy_image(manuscript, remove_container_info=True):
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.proxy_image_name, force=True)
    if(remove_container_info):
        container_info.proxy_image_name = ""
        container_info.save()

def start_repo2docker_container(manuscript):
    container_info = manuscript.manuscript_containerinfo
    print("start_repo2docker_container")
    print(container_info.__dict__)

# #TODO: Probably shouldn't do this, we handle it elsewhere? I could also delete the ID in a different place...
#     if(container_info.repo_container_id):
#         stop_delete_repo2docker_container(manuscript, remove_container_info=False)
#         container_info.repo_container_id = ""

    # if(!container_info.container_port): #we reuse existing port/ip on recreation
    #     while True:
    #         container_info.repo_container_port = random.randint(50000, 50019)
    #         if not m.ContainerInfo.objects.filter(Q(repo_container_port=container_port) | Q(proxy_container_port=container_port)).exists():
    #             break
    if(not container_info.repo_container_ip): 
        container_info.repo_container_ip = "0.0.0.0"

    client = docker.from_env()    
    run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' " #--NotebookApp.allow_origin='*'
    #TODO: Set the "*" to be more specific
    run_string += "--NotebookApp.tornado_settings=\"{ 'headers': { 'Content-Security-Policy': \\\"frame-ancestors 'self' *\\\" } }\""

    print(run_string)

    container = client.containers.run(container_info.repo_image_name, run_string,  detach=True) #network=container_info.container_network_name()) #ports={'8888/tcp': container_port},
    notebook_network = client.networks.get(container_info.container_network_name())
    notebook_network.connect(container, ipv4_address=container_info.network_ip_substring + ".2")

    container_info.repo_container_id = container.id
    container_info.save()

#TODO: implement all the remove_container_infos
def stop_delete_repo2docker_container(manuscript, remove_container_info=True):
    stop_delete_container(manuscript.manuscript_containerinfo.repo_container_id)
    if(remove_container_info):
        container_info.repo_container_id = ""
        container_info.repo_container_ip = ""
        container_info.save()


# TODO: There are 3 cases where I'd run start:
#        1. New notebook creation - after submission file upload
#        2. Recreating after file upload
#        3. Recreating after user access has been changed
# 2. we need to delete the juptyer notebook but not the proxy (if we do it right)
# 3. we need to delete the proxy but not the notebook (if we do it right)
# I should probably check back with the previous notebook create code for the right way to do this. Also think more if the logic should really be in here?
def start_oauthproxy_container(manuscript): 
    container_info = manuscript.manuscript_containerinfo

# #TODO: Probably shouldn't do this, we handle it elsewhere. I could also delete the ID in a different place...
#     if(container_info.proxy_container_id):
#         stop_delete_oauthproxy_container(manuscript, remove_container_info=False)
#         container_info.proxy_container_id = ""

    #If the info previously exists for the 
    if(not container_info.proxy_container_port):
        while True:
            container_info.proxy_container_port = random.randint(50020, 50039)
            if not m.ContainerInfo.objects.filter(proxy_container_port=container_info.proxy_container_port).exists():
                break
    if(not container_info.proxy_container_ip):
        container_info.proxy_container_ip = "localhost"
    
    run_string = ""
    client = docker.from_env()

    emails_file_path = "/opt/bitnami/oauth2-proxy/authenticated_emails.txt"

    #            + "--whitelist-domain=" + "'" + container_info.proxy_container_ip+":"+str(container_info.proxy_container_port) + "'" + " " \
    #            + "--email-domain=" + "'*'" + " " \
    command = "--http-address=" + "'0.0.0.0:4180'" + " " \
            + "--https-address=" + "':443'" + " " \
            + "--redirect-url=" + "'http://"+container_info.proxy_container_ip+":"+str(container_info.proxy_container_port) + "/oauth2/callback' " \
            + "--upstream=" + "'http://" +container_info.network_ip_substring+ ".2:8888" + "/' " \
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
            + "--cookie-httponly=" + "'true'" + " " \
            + "--authenticated-emails-file=" + "'" + emails_file_path + "'" + " " \

    if(settings.DEBUG):
        command += "--cookie-secure=" + "'false'" + " "
    else:
        command += "--cookie-secure=" + "'true'" + " "
    print("OAUTH PROXY COMMAND: " + command)

    container = client.containers.run(container_info.proxy_image_name, command, ports={'4180/tcp': container_info.proxy_container_port}, detach=True) #network=container_info.container_network_name())

    container_info.proxy_container_id = container.id
    container_info.save()

    # #Janky log access code
    # import time
    # time.sleep(5)
    # print(container.logs()) #Should find a better way to stream these logs. Though you can get to them via docker.

    notebook_network = client.networks.get(container_info.container_network_name())
    notebook_network.connect(container, ipv4_address=container_info.network_ip_substring + ".3")

    return container_info.container_public_address()
    
def update_oauthproxy_container_authenticated_emails(manuscript):
    #What should we do if there is no container yet? Error or just do nothing?
    container_info = manuscript.manuscript_containerinfo
    _write_oauthproxy_email_list_to_working_directory(manuscript)

    docker_build_folder = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/"

    run_string = "docker cp authenticated_emails.txt " + container_info.proxy_container_id +":/opt/bitnami/oauth2-proxy/authenticated_emails.txt"
    result = subprocess.run([run_string], shell=True, capture_output=True, cwd=docker_build_folder)

    logger.debug("update_oauthproxy_container_authenticated_emails result:" + str(result))


def stop_delete_oauthproxy_container(manuscript, remove_container_info=True):
    stop_delete_container(manuscript.manuscript_containerinfo.proxy_container_id)
    if(remove_container_info):
        container_info.proxy_container_id = ""
        container_info.proxy_container_ip = ""
        container_info.proxy_container_port = ""
        container_info.save()

def stop_delete_container(container_id):
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.stop(timeout=2) #should I just use kill?
    container.remove()

#Note: this does not handle recreation like the container code.
def start_network(manuscript):
    while True: #get an unused subnet.
        network_part_2 = random.randint(0, 255)
        network_sub = "172." + str(network_part_2) + ".0"
        if not m.ContainerInfo.objects.filter(network_ip_substring=network_sub).exists():
            break

    client = docker.from_env()
    container_info = manuscript.manuscript_containerinfo
    container_info.network_ip_substring = network_sub

    ipam_pool = docker.types.IPAMPool(
        subnet=network_sub + '.0/16',
        gateway=network_sub + '.1'
    )
    ipam_config = docker.types.IPAMConfig(
        pool_configs=[ipam_pool]
    )

    network = client.networks.create(container_info.container_network_name(), driver="bridge", ipam=ipam_config)
    container_info.network_id = network.id
    container_info.save()

def delete_network(manuscript, remove_container_info=True):
    client = docker.from_env()
    network = client.networks.get(manuscript.manuscript_containerinfo.network_id)
    network.remove()
    if(remove_container_info):
        container_info.network_ip_substring = ""
        container_info.network_id = ""
        container_info.save()

def delete_manuscript_docker_stack(manuscript, remove_container_info=False):
    #Note we don't use these methods "remove_container_info" because we just blast away the whole thing at the end
    try:
        stop_delete_oauthproxy_container(manuscript, remove_container_info=False)
        stop_delete_repo2docker_container(manuscript, remove_container_info=False)
        delete_network(manuscript, remove_container_info=False)
        delete_repo2docker_image(manuscript, remove_container_info=False)
        delete_oauth2proxy_image(manuscript, remove_container_info=False)

        if remove_container_info:
            manuscript.manuscript_containerinfo.delete()
            return("Manuscript stack and ContainerInfo deleted")
            
        return("Manuscript stack deleted")

    except m.ContainerInfo.DoesNotExist:
        return("No ContainerInfo found, so stack was not deleted. Possibly it was never created.")

#This deletes the stack via tags based on manuscript id, not via info from ContainerInfo
#In the end its probably not much different, but its being designed to use only for admins
def delete_manuscript_docker_stack_crude(manuscript):
    #delete containers via tags
    try:
        run_string = "docker ps -a |  grep ':" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id) + "' | awk '{print $1}' | xargs docker rm -f"
        print(subprocess.run([run_string], shell=True, capture_output=True))
        
        #delete images via tags. note the lack of a colon.
        run_string = "docker images | grep '" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id) + "' | awk '{print $3}' | xargs docker rmi"
        print(subprocess.run([run_string], shell=True, capture_output=True))
        
        #delete all unused networks
        run_string = "docker network prune -f"
        print(subprocess.run([run_string], shell=True, capture_output=True))

        manuscript.manuscript_containerinfo.delete()
        return("Manuscript stack and ContainerInfo deleted")

    except m.ContainerInfo.DoesNotExist:
        return("No ContainerInfo found, so stack was not deleted. Possibly it was never created.")

def build_manuscript_docker_stack(manuscript, refresh_notebook_if_up=False):
    print("RECREATE DOCKERS IN OPEN BINDER")

    build_repo2docker_image(manuscript)
    build_oauthproxy_image(manuscript)
    start_network(manuscript)
    start_repo2docker_container(manuscript)
    start_oauthproxy_container(manuscript)

def refresh_notebook_stack(manuscript):
    stop_delete_repo2docker_container(manuscript, remove_container_info=False)
    delete_repo2docker_image(manuscript, remove_container_info=False)
    build_repo2docker_image(manuscript)
    start_repo2docker_container(manuscript)

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




#I've gotten really close to getthing these two containers to talk together. Something is up with the networking. I think they can talk together via ip, but not via their names?
#Maybe something is up with the python-docker library, maybe it doesn't alias by default? But I added the alias and it still doesn't work
#Also worth noting that we should change the "ID" fields in container_info to name if we keep using them that way