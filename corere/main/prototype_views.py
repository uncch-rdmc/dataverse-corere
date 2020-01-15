from django.shortcuts import render, redirect, resolve_url
from django.conf import settings
from corere.main.models import User, Catalog
import requests, urllib, os, time, json, base64, logging
from os import walk
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import logout
from django.contrib import messages
from django.core.files.storage import default_storage

OUTPUT = os.environ["UPLOAD_OUTPUT_PATH"]

logger = logging.getLogger('corere')

def index(request):
    logger.debug(request.user.username)
    if request.user.is_authenticated:
        return render(request, "main/index.html")
    else: 
        return render(request, "main/login.html")

#TODO: Ensure all return paths do what we want. They were changed after the port and may never have been exercised
def create_import_init(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            if request.POST.get('import'):
                if request.POST.get('url') and request.POST.get('persistID') and request.POST.get('token') \
                    and request.POST.get('version'):
                    
                    url = request.POST.get('url')
                    key = request.POST.get('token')

                    persistID = request.POST.get('persistID')

                    fileIds = request.POST.getlist('fileIds[]')
                    fileNames = request.POST.getlist('fileNames[]')
                    
                    ## GET Metadata Blocks for dataset
                    META_URL = url+"/api/datasets/export?exporter=ddi&persistentId="+persistID
                    meta_download = requests.get(META_URL,allow_redirects=True)
                    meta_content = meta_download.content
                    open(OUTPUT+"/metadata.xml", 'wb').write(meta_content)

                    # Make Directory if it doesn't exist
                    if not os.path.exists(OUTPUT+"/"+request.user.username):
                        os.mkdir(OUTPUT+"/"+request.user.username)

                    ## Download files to a folder
                    for name,ids in zip(fileNames,fileIds):
                        FILE_Q = url+"/api/access/datafile/"+ids+"/?persistentId=doi:"+persistID+"&key="+key
                        r = requests.get(FILE_Q,allow_redirects=True)
                        
                        open(OUTPUT+"/"+request.user.username+"/"+name, 'wb').write(r.content)
                    return HttpResponse(status=204) 
                return HttpResponse(status=422) 
    return JsonResponse(request.values.get('files'))


def uploadfiles(request):
    if request.method == 'POST':
        logger.debug(request.FILES)
        file_obj = request.FILES.get('file')
        file_name = str(file_obj)

        #This chunking may be unnessecary, and default_store.save could be used instead. unsure.
        with default_storage.open('./temp/'+file_name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

    return HttpResponse(status=204) #In flask this returned text, but I don't think it was used in any way

def logout_view(request):
    logout(request)
    messages.add_message(request, messages.INFO, 'You have succesfully logged out!')
    return redirect('proto_root')

def create_or_import(request):
    logger.debug(request.user.username)
    if request.user.is_authenticated:
        Catalog.objects.create(user_id=request.user)
        return render(request, "main/create_import.html")
    else:
       return redirect('proto_root')

def create_catalog(request):
    logger.debug(request.user.username)
    if request.user.is_authenticated:
        Catalog.objects.create(user_id=request.user)
        return render(request, "main/create.html")
    else:
       return redirect('proto_root')

def load(request):
    logger.debug("test")
    myfiles = []

    for (dirpath, dirnames, filenames) in walk('./temp/'):
        for filename in filenames:
            if ".DS" not in filename:
                with open(dirpath+"/"+ filename, "rb") as f:
                    text = f.read().strip()

                    encoded = base64.b64encode(text).decode("utf-8")
                    z = {
                        "action": "create",
                        "file_path": filename,
                        "encoding": "base64",
                        "content": encoded
                    }
                    myfiles.append(z)

  
    logger.debug("test2")
    runtime = {
        "action": "create",
        "file_path": "runtime.txt",
        "content": "r-2018-02-05"
    }
    myfiles.append(runtime)

    requirements = {
        "action": "create",
        "file_path": "requirements.txt",
        "content": """
        jupyterlab==0.35.6
        """
    }
    myfiles.append(requirements)

    gitignore = {
        "action": "create",
        "file_path": ".gitignore",
        "content": """.gitconfig
.yarn/
.npm/
.local/
.ipython/
.ipynb_checkpoints/
.bash_logout
.bashrc
.cache/
.conda/
.config/
.profile/
.profile
.jupyter/
        \r\n
        """
    }
    myfiles.append(gitignore)


    postBuild = {
        "action": "create",
        "file_path": "postBuild",
        "content": """#!/bin/bash

jupyter labextension install @lckr/jupyterlab_variableinspector
jupyter labextension install @jupyterlab/celltags
jupyter labextension install @andreyodum/core2
pip install jupyterlab-git
jupyter serverextension enable --py jupyterlab_git
rm -rf requirements.txt runtime.txt

git config --global user.email "{0}"
git config --global user.name "{1}"
git rm -r --cached .
git remote set-url origin {2}

\r\n
""".format(request.user.first_name, request.user.first_name+" "+request.user.last_name, settings.GIT_CONFIG_URL)
    }

    logger.debug("test3")
    # jupyter labextension install @andreyodum/core2 
    myfiles.append(postBuild)


    #TEMPORARY
    ### In the future, please follow this link https://binderhub.readthedocs.io/en/latest/setup-binderhub.html
    ### and setup GitLabRepoProvider with private token TO ENSURE THAT GITLAB PROJECTS ARE ALL PRIVATE

    GITLAB_API = settings.GIT_LAB_URL+"/"+settings.GIT_API_VERSION
    PRIVATE_TOKEN = "private_token="+settings.GIT_PRIVATE_TOKEN
    headers = {'PRIVATE-TOKEN': ''+settings.GIT_PRIVATE_TOKEN+'',
                'Content-Type': 'application/json'}

    logger.debug("test4")
    username = "test"
    
    logger.debug(GITLAB_API)
    logger.debug(PRIVATE_TOKEN)
    logger.debug(GITLAB_API+"/projects/"+urllib.parse.quote("root/"+username, safe='')+"/?"+PRIVATE_TOKEN)
    requests.delete(GITLAB_API+"/projects/"+urllib.parse.quote("root/"+username, safe='')+"/?"+PRIVATE_TOKEN)
    while 1:
        r_project = requests.post(GITLAB_API+"/projects/?"+PRIVATE_TOKEN, data={"name": username, "visibility":"public"})
        if r_project.status_code == 201:
            break
        time.sleep(1)
    logger.debug("test5")
    if r_project.status_code != 201:
        logger.debug(r_project.content)
        raise ValueError
       #return "ERROR" + str(r_project.status_code) + " CONENTE: "+str(r_project.content)
    
    gitlabid = str(json.loads(r_project.content)['id'])
    logger.debug("GITLABID" + gitlabid)
    

    r_put = requests.put(GITLAB_API+"projects/"+gitlabid+"/services/emails-on-push?&"+PRIVATE_TOKEN, 
        json={"recipients": settings.RECIPIENTS, "disable_diffs": False, "send_from_committer_email": False
        }
        )

    r_commit = requests.post(GITLAB_API+"projects/"+gitlabid+"/repository/commits?&"+PRIVATE_TOKEN, 
        json={"branch": "master", "author_email": "admin@example.com", "author_name": "Administrator",
            "commit_message": "step2", "actions": myfiles
        }
        )

    logger.debug(r_commit.content)
    
    code = json.loads(r_commit.content)['id']
    return JsonResponse({"status":"Success","Code":code,"URI": settings.GIT_LAB_URL+"/root/"+username})