import docker, logging, subprocess, random, io, os, time
import shutil
from django.conf import settings
from corere.main import git as g
from corere.main import models as m
from corere.main import constants as c
from django.db.models import Q
logger = logging.getLogger(__name__)

#TODO: Better error checking. stderr has concents even when its successful.
def build_repo2docker_image(manuscript):
    logger.debug("Begin build_repo2docker_image for manuscript: " + str(manuscript.id))
    path = g.get_submission_repo_path(manuscript)
    sub_version = manuscript.get_max_submission_version_id()
    image_name = ("jupyter-" + str(manuscript.id) + "-" + manuscript.slug + "-version" + str(sub_version))[:128] + ":" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id) 
    run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"

    #this happens first so we create the folder and reset the file (with 'w' instead of 'a')
    build_log_path = get_build_log_path(manuscript)
    os.makedirs(os.path.dirname(build_log_path), exist_ok=True)
    with open(build_log_path, 'w+') as logfile: 
        result = subprocess.run([run_string], shell=True, stdout=logfile, stderr=subprocess.STDOUT)
    logger.debug("build_repo2docker_image for manuscript: "+ str(manuscript.id) + ". Result:" + str(result))

    manuscript.manuscript_containerinfo.repo_image_name = image_name
    manuscript.manuscript_containerinfo.submission_version = sub_version
    manuscript.manuscript_containerinfo.manuscript = manuscript
    manuscript.manuscript_containerinfo.save()

def delete_repo2docker_image(manuscript):
    logger.debug("Begin delete_repo2docker_image for manuscript: " + str(manuscript.id))
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.repo_image_name, force=True)

def _write_oauthproxy_email_list_to_working_directory(manuscript):
    logger.debug("Begin _write_oauthproxy_email_list_to_working_directory for manuscript: " + str(manuscript.id))
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
        email_file.write(ue.get("email")+"\n")

    email_file.close()

def _write_oauth_proxy_html_templates_to_working_directory(manuscript):
    logger.debug("Begin _write_oauth_proxy_html_templates_to_working_directory for manuscript: " + str(manuscript.id))
    container_info = manuscript.manuscript_containerinfo
    client = docker.from_env()    

    email_file_path = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/email-templates"

    if os.path.exists(email_file_path) and os.path.isdir(email_file_path):
        shutil.rmtree(email_file_path)

    #/Users/madunlap/Documents/GitHub/dataverse-corere/corere   /main/static/oauth2-proxy/email-templates
    shutil.copytree(settings.BASE_DIR + "/main/static/oauth2-proxy/email-templates", email_file_path )

def build_oauthproxy_image(manuscript):
    logger.debug("Begin build_oauthproxy_image for manuscript: " + str(manuscript.id))
    container_info = manuscript.manuscript_containerinfo
    client = docker.from_env()    

    _write_oauthproxy_email_list_to_working_directory(manuscript)
    _write_oauth_proxy_html_templates_to_working_directory(manuscript)

    docker_build_folder = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/"
    dockerfile_path = docker_build_folder + "dockerfile"
    docker_string = "FROM " + settings.DOCKER_OAUTH_PROXY_BASE_IMAGE + "\n" \
                  + "COPY authenticated_emails.txt /opt/bitnami/oauth2-proxy/authenticated_emails.txt \n" \
                  + "ADD email-templates /opt/bitnami/oauth2-proxy/email-templates"
    with open(dockerfile_path, 'w') as f:
        f.write(docker_string)

    #run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"
    container_info.proxy_image_name = ("oauthproxy-" + str(manuscript.id) + "-" + manuscript.slug)[:128] + ":" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id)
    container_info.save()
    run_string = "docker build . -t " + container_info.proxy_image_name

    with open(get_build_log_path(manuscript), 'a+') as logfile: 
        result = subprocess.run([run_string], shell=True, stdout=logfile, stderr=subprocess.STDOUT, cwd=docker_build_folder)

    logger.debug("build_oauthproxy_image result:" + str(result))


def delete_oauth2proxy_image(manuscript):
    logger.debug("Begin delete_oauth2proxy_image for manuscript: " + str(manuscript.id))
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.proxy_image_name, force=True)

def start_repo2docker_container(manuscript):
    logger.debug("Begin start_repo2docker_container for manuscript: " + str(manuscript.id))
    container_info = manuscript.manuscript_containerinfo

    if(not container_info.repo_container_ip): 
        container_info.repo_container_ip = "0.0.0.0"

    #NOTE: THIS IS COPIED FROM start_oauthproxy_container. We have to know the proxy port here though so we can set the allow_origin.
    #If the info previously exists for the 
    if(not container_info.proxy_container_port):
        while True:
            #TODO: Random is pretty inefficient if the space is maxed. We should maybe start at a random and increment up
            if(settings.CONTAINER_PROTOCOL == 'https'):
                container_info.proxy_container_port = random.randint(50020-20, 50039-20)
            else:
                container_info.proxy_container_port = random.randint(50020, 50039)
            
            if not m.ContainerInfo.objects.filter(proxy_container_port=container_info.proxy_container_port).exists():
                break
    if(not container_info.proxy_container_address):
        container_info.proxy_container_address = settings.CONTAINER_ADDRESS

    print("PUBLIC ADDRESS BEFORE REPO2DOCKER LAUNCH")
    print(container_info.container_public_address())
    print(container_info.container_public_address()+"/view/globus_logo_white.png")

    client = docker.from_env()    
    #origin_addr = settings.CONTAINER_PROTOCOL + "://" + container_inf.proxy_container_address + ":" + str(container_info.proxy_container_port) #note, not adding 20
    #run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='"+ origin_addr +"'"
    run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='"+container_info.container_public_address() +"'"
    #run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='*'"
    #run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='"+container_info.container_public_address() +"/view/globus_logo_white.png'"
    #TODO: Maybe set the '*' to specify only corere's host. 
    run_string += "--NotebookApp.tornado_settings=\"{ 'headers': { 'Content-Security-Policy': \\\"frame-ancestors 'self' *\\\" } }\""   

    #Add this if you need direct access. Defeats the whole point of a proxy. # ports={'8888/tcp': "60000"},
    container = client.containers.run(container_info.repo_image_name, run_string, detach=True, network=container_info.container_network_name())

    while container.status != "created": #This is a really lazy means of waiting for the container to complete
        print(container.status)
        time.sleep(.1)
    #TODO: This never seems to have any contents. Maybe because when created first starts there is nothing?
    print(container.logs())
    print(container.logs(), file=open(get_build_log_path(manuscript), "a"))

    notebook_network = client.networks.get(container_info.container_network_name())
    notebook_network.disconnect(container, force=True) #we disconnect it and then re-add it with the correct ip. I couldn't find a way to start the contain with no network and then just add this.
    notebook_network.connect(container, ipv4_address=container_info.network_ip_substring + ".2")

    container_info.repo_container_id = container.id
    container_info.save()

def stop_delete_repo2docker_container(manuscript):
    logger.debug("Begin stop_delete_repo2docker_container for manuscript: " + str(manuscript.id))
    stop_delete_container(manuscript.manuscript_containerinfo.repo_container_id)

#We need the request to get the server address to pass to oauth2-proxy. Technically we only need this when creating the back button but we require it anyways.
def start_oauthproxy_container(manuscript, request): 
    logger.debug("Begin start_oauthproxy_container for manuscript: " + str(manuscript.id))
    container_info = manuscript.manuscript_containerinfo

    #NOTE: THIS LOGIC IS RARELY CALLED BECAUSE WE ALREADY DO THE SAME LOGIC IN REPO2DOCKER. WE HAVE TO KNOW THE PORT BEFORE LAUNCHING THAT CONTAINER TO SET allow-origin.
    #If the info previously exists for the 
    if(not container_info.proxy_container_port):
        while True:
            #TODO: Random is pretty inefficient if the space is maxed. We should maybe start at a random and increment up
            if(settings.CONTAINER_PROTOCOL == 'https'):
                container_info.proxy_container_port = random.randint(50020-20, 50039-20)
            else:
                container_info.proxy_container_port = random.randint(50020, 50039)
            
            if not m.ContainerInfo.objects.filter(proxy_container_port=container_info.proxy_container_port).exists():
                break
    if(not container_info.proxy_container_address):
        container_info.proxy_container_address = settings.CONTAINER_ADDRESS
    
    run_string = ""
    client = docker.from_env()

    emails_file_path = "/opt/bitnami/oauth2-proxy/authenticated_emails.txt"
    template_files_path = "/opt/bitnami/oauth2-proxy/email-templates"
    latest_submission = manuscript.get_latest_submission()

    #Note: We have hijacked "footer" to instead pass the corere server address to our custom oauth2-proxy template
    #Note: host.docker.internal may have issues on linux.
    #Note: whitelist-domain is used to allow redirects after using the oauth2 sign-in direct url
    command = "--http-address=" + "'0.0.0.0:4180'" + " " \
            + "--https-address=" + "'0.0.0.0:443'" + " " \
            + "--redirect-url=" + "'" + container_info.container_public_address() + "/oauth2/callback' " \
            + "--upstream=" + "'http://" +container_info.network_ip_substring+ ".2:8888" + "/' " \
            + "--upstream=" + "'"+ settings.CONTAINER_PROTOCOL + "://"+ settings.SERVER_ADDRESS +"/submission/" + str(latest_submission.id) + "/notebooklogin/' " \
            + "--provider=" + "'oidc'" + " " \
            + "--provider-display-name=" + "'Globus'" + " " \
            + "--oidc-issuer-url=" + "'https://auth.globus.org'" + " " \
            + "--cookie-name=" + "'_oauth2_proxy'" + " " \
            + "--client-id=" + "'" + settings.SOCIAL_AUTH_GLOBUS_KEY + "'" + " " \
            + "--client-secret=" + "'" + settings.SOCIAL_AUTH_GLOBUS_SECRET + "'" + " " \
            + "--cookie-secret=" + "'" + settings.OAUTHPROXY_COOKIE_SECRET + "'" + " " \
            + "--cookie-refresh=" + "'0s'" + " " \
            + "--cookie-expire=" + "'168h'" + " " \
            + "--authenticated-emails-file=" + "'" + emails_file_path + "'" + " " \
            + "--custom-templates-dir='" + template_files_path + "' " \
            + "--banner=" + "'" + "Please re-authenticate to access the environment for Manuscript: " + manuscript.title + "'" + " " \
            + "--footer=" + "'" + settings.CONTAINER_PROTOCOL + "://" + settings.SERVER_ADDRESS + "'" + " " \
            + "--whitelist-domain=" + "'" + settings.SERVER_ADDRESS + "'" + " "

    if(settings.CONTAINER_PROTOCOL == 'https'):
        command += "--cookie-secure=" + "'true'" + " "
    else:
        command += "--cookie-secure=" + "'false'" + " "
    
    container = client.containers.run(container_info.proxy_image_name, command, ports={'4180/tcp': container_info.proxy_container_port}, detach=True) 

    #network=container_info.container_network_name())
    while container.status != "created": #This is a really lazy means of waiting for the container to complete
        print(container.status)
        time.sleep(.1)
    #TODO: This never seems to have any contents. Maybe because when created first starts there is nothing?
    print(container.logs())
    print(container.logs(), file=open(get_build_log_path(manuscript), "a"))

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
    logger.debug("Begin update_oauthproxy_container_authenticated_emails for manuscript: " + str(manuscript.id))
    container_info = manuscript.manuscript_containerinfo
    _write_oauthproxy_email_list_to_working_directory(manuscript)

    docker_build_folder = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/"

    run_string = "docker cp authenticated_emails.txt " + container_info.proxy_container_id +":/opt/bitnami/oauth2-proxy/authenticated_emails.txt"
    result = subprocess.run([run_string], shell=True, capture_output=True, cwd=docker_build_folder)

    logger.debug("update_oauthproxy_container_authenticated_emails result:" + str(result))


def stop_delete_oauthproxy_container(manuscript):
    logger.debug("Begin stop_delete_oauthproxy_container for manuscript: " + str(manuscript.id))
    stop_delete_container(manuscript.manuscript_containerinfo.proxy_container_id)

def stop_delete_container(container_id):
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.stop(timeout=2) #should I just use kill?
    container.remove()

#Note: this does not handle recreation like the container code.
def start_network(manuscript):
    logger.debug("Begin start_network for manuscript: " + str(manuscript.id))
    while True: #get an unused subnet.
        network_part_2 = random.randint(10, 255)
        network_sub = "10." + str(network_part_2) + ".255"
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

def delete_network(manuscript):
    logger.debug("Begin delete_network for manuscript: " + str(manuscript.id))
    client = docker.from_env()
    network = client.networks.get(manuscript.manuscript_containerinfo.network_id)
    network.remove()

def delete_manuscript_docker_stack(manuscript):
    logger.debug("Begin delete_manuscript_docker_stack for manuscript: " + str(manuscript.id))
    try:
        stop_delete_oauthproxy_container(manuscript)
        stop_delete_repo2docker_container(manuscript)
        delete_network(manuscript)
        delete_repo2docker_image(manuscript)
        delete_oauth2proxy_image(manuscript)

        manuscript.manuscript_containerinfo.delete()
        return("Manuscript stack and ContainerInfo deleted")

    except m.ContainerInfo.DoesNotExist:
        return("No ContainerInfo found, so stack was not deleted. Possibly it was never created.")

#This deletes the stack via tags based on manuscript id, not via info from ContainerInfo
#In the end its probably not much different, but its being designed to use only for admins
#TODO: If you delete the last stack with this method, starting up a new stack is very slow.
#      I assume this has to do with deletion of intermediates, or the docker network prune.
#      It would be good to fix this.
def delete_manuscript_docker_stack_crude(manuscript):
    logger.debug("Begin delete_manuscript_docker_stack_crude for manuscript: " + str(manuscript.id))
    try:
        #delete containers via tags
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

def build_manuscript_docker_stack(manuscript, request, refresh_notebook_if_up=False):
    logger.debug("Begin build_manuscript_docker_stack for manuscript: " + str(manuscript.id))
    if (not (hasattr(manuscript, 'manuscript_containerinfo'))):
        m.ContainerInfo().manuscript = manuscript

    manuscript.manuscript_containerinfo.build_in_progress = True
    manuscript.manuscript_containerinfo.save()

    build_repo2docker_image(manuscript)
    build_oauthproxy_image(manuscript)
    start_network(manuscript)
    start_repo2docker_container(manuscript)
    start_oauthproxy_container(manuscript, request)

    manuscript.manuscript_containerinfo.build_in_progress = False
    manuscript.manuscript_containerinfo.save()

def refresh_notebook_stack(manuscript):
    logger.debug("Begin refresh_notebook_stack for manuscript: " + str(manuscript.id))
    if (not (hasattr(manuscript, 'manuscript_containerinfo'))):
        m.ContainerInfo().manuscript = manuscript

    manuscript.manuscript_containerinfo.build_in_progress = True
    manuscript.manuscript_containerinfo.save()

    stop_delete_repo2docker_container(manuscript)
    delete_repo2docker_image(manuscript)
    build_repo2docker_image(manuscript)
    start_repo2docker_container(manuscript)

    manuscript.manuscript_containerinfo.build_in_progress = False
    manuscript.manuscript_containerinfo.save()
            
def get_build_log_path(manuscript):
    return settings.DOCKER_BUILD_FOLDER + "/docker-build-logs/" + str(manuscript.id) + ".log"
