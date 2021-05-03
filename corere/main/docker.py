import docker, logging, subprocess, random, io, os
import shutil
from django.conf import settings
from corere.main import git as g
from corere.main import models as m
from corere.main import constants as c
from django.db.models import Q
logger = logging.getLogger(__name__)

#TODO: Better error checking. stderr has concents even when its successful.
def build_repo2docker_image(manuscript):
    path = g.get_submission_repo_path(manuscript)
    sub_version = manuscript.get_max_submission_version_id()
    image_name = ("jupyter-" + str(manuscript.id) + "-" + manuscript.slug + "-version" + str(sub_version))[:128] + ":" + settings.DOCKER_GEN_TAG + "-" + str(manuscript.id) 
    run_string = "jupyter-repo2docker --no-run --json-logs --image-name '" + image_name + "' '" + path + "'"
    result = subprocess.run([run_string], shell=True, capture_output=True)
    logger.debug("build_repo2docker_image for manuscript: "+ str(manuscript.id) + ". Result:" + str(result))

    #TODO: should this logic be moved outside of this function. Is it needed in other places?
    if (not (hasattr(manuscript, 'manuscript_containerinfo'))):
        container_info = m.ContainerInfo() 
    else:
        container_info = manuscript.manuscript_containerinfo
    container_info.repo_image_name = image_name
    container_info.submission_version = sub_version
    container_info.manuscript = manuscript
    container_info.save()

def delete_repo2docker_image(manuscript):
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.repo_image_name, force=True)

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
        email_file.write(ue.get("email")+"\n")

    email_file.close()

def _write_oauth_proxy_html_templates_to_working_directory(manuscript):
    container_info = manuscript.manuscript_containerinfo
    client = docker.from_env()    

    email_file_path = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/email-templates"

    if os.path.exists(email_file_path) and os.path.isdir(email_file_path):
        shutil.rmtree(email_file_path)

    #/Users/madunlap/Documents/GitHub/dataverse-corere/corere   /main/static/oauth2-proxy/email-templates
    shutil.copytree(settings.BASE_DIR + "/main/static/oauth2-proxy/email-templates", email_file_path )

def build_oauthproxy_image(manuscript):
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
    result = subprocess.run([run_string], shell=True, capture_output=True, cwd=docker_build_folder)

    logger.debug("build_oauthproxy_image result:" + str(result))


def delete_oauth2proxy_image(manuscript):
    client = docker.from_env()
    client.images.remove(image=manuscript.manuscript_containerinfo.proxy_image_name, force=True)

def start_repo2docker_container(manuscript):
    container_info = manuscript.manuscript_containerinfo
    logger.debug("start_repo2docker_container for manuscript: " + str(manuscript.id))

    if(not container_info.repo_container_ip): 
        container_info.repo_container_ip = "0.0.0.0"

    client = docker.from_env()    
    run_string = "jupyter notebook --ip " + container_info.repo_container_ip + " --NotebookApp.token='' --NotebookApp.password='' " #--NotebookApp.allow_origin='*'
    #TODO: Maybe set the '*' to specify only corere's host. 
    run_string += "--NotebookApp.tornado_settings=\"{ 'headers': { 'Content-Security-Policy': \\\"frame-ancestors 'self' *\\\" } }\""   


    #Add this if you need direct access. Defeats the whole point of a proxy. # ports={'8888/tcp': "60000"},
    container = client.containers.run(container_info.repo_image_name, run_string, detach=True)
    notebook_network = client.networks.get(container_info.container_network_name())
    notebook_network.connect(container, ipv4_address=container_info.network_ip_substring + ".2")

    container_info.repo_container_id = container.id
    container_info.save()

def stop_delete_repo2docker_container(manuscript):
    stop_delete_container(manuscript.manuscript_containerinfo.repo_container_id)

#We need the request to get the server address to pass to oauth2-proxy. Technically we only need this when creating the back button but we require it anyways.
def start_oauthproxy_container(manuscript, request): 
    container_info = manuscript.manuscript_containerinfo

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
    template_files_path = "/opt/bitnami/oauth2-proxy/email-templates"

    #+ "--cookie-httponly=" + "'true'" + " " \
    #            + "--whitelist-domain=" + "'" + container_info.proxy_container_ip+":"+str(container_info.proxy_container_port) + "'" + " " \
    #            + "--email-domain=" + "'*'" + " " \
    
                #+ "--upstream=" + "'http://0.0.0.0:8000/submission/49/notebook/' " \

    #            + "--banner=" + "'" + "Please authenticate to access the environment for Manuscript: " + manuscript.title + "'" + " " \
    #            + "--footer=" + "'" + "<button onclick=\"window.history.back();\" type=\"button\" class=\"btn btn-secondary btn-sm\" data-toggle=\"tooltip\" data-placement=\"auto\" title=\"button\">Back</button> Please re-authenticate to access the environment for Manuscript: " + manuscript.title + "'" + " " \

    latest_submission = manuscript.get_latest_submission()



    if(request.is_secure()):
        host_and_handler = "https://" + request.get_host()
    else:
        host_and_handler = "http://" + request.get_host()
    #Note: We have hijacked "footer" to instead pass the corere server address to our custom oauth2-proxy template
    #Note: host.docker.internal may have issues on linux.
    #Note: whitelist-domain is used to allow redirects after using the oauth2 sign-in direct url
    command = "--http-address=" + "'0.0.0.0:4180'" + " " \
            + "--https-address=" + "':443'" + " " \
            + "--redirect-url=" + "'http://"+container_info.proxy_container_ip+":"+str(container_info.proxy_container_port) + "/oauth2/callback' " \
            + "--upstream=" + "'http://" +container_info.network_ip_substring+ ".2:8888" + "/' " \
            + "--upstream=" + "'http://host.docker.internal:8000/submission/" + str(latest_submission.id) + "/notebooklogin/' " \
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
            + "--footer=" + "'" + host_and_handler + "'" + " " \
            + "--whitelist-domain=" + "'" + request.get_host() + "'" + " "

    if(settings.DEBUG):
        command += "--cookie-secure=" + "'false'" + " "
    else:
        command += "--cookie-secure=" + "'true'" + " "

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
    container_info = manuscript.manuscript_containerinfo
    _write_oauthproxy_email_list_to_working_directory(manuscript)

    docker_build_folder = settings.DOCKER_BUILD_FOLDER + "/oauthproxy-" + str(manuscript.id) + "/"

    run_string = "docker cp authenticated_emails.txt " + container_info.proxy_container_id +":/opt/bitnami/oauth2-proxy/authenticated_emails.txt"
    result = subprocess.run([run_string], shell=True, capture_output=True, cwd=docker_build_folder)

    logger.debug("update_oauthproxy_container_authenticated_emails result:" + str(result))


def stop_delete_oauthproxy_container(manuscript):
    stop_delete_container(manuscript.manuscript_containerinfo.proxy_container_id)

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

def delete_network(manuscript):
    client = docker.from_env()
    network = client.networks.get(manuscript.manuscript_containerinfo.network_id)
    network.remove()

def delete_manuscript_docker_stack(manuscript):
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
    build_repo2docker_image(manuscript)
    build_oauthproxy_image(manuscript)
    start_network(manuscript)
    start_repo2docker_container(manuscript)
    start_oauthproxy_container(manuscript, request)

def refresh_notebook_stack(manuscript):
    stop_delete_repo2docker_container(manuscript)
    delete_repo2docker_image(manuscript)
    build_repo2docker_image(manuscript)
    start_repo2docker_container(manuscript)