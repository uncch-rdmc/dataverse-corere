import requests, logging, os, urllib, json, pprint
import sseclient
from django.http import Http404
logger = logging.getLogger(__name__)  

def binder_build_load(manuscript):
    print("BINDER ADDR:")
    print(os.environ["BINDER_ADDR"])

    gitlab_url = urllib.parse.quote( (os.environ["GIT_LAB_URL"] + "/root/"+manuscript.gitlab_submissions_path), safe='')

    #yes, we have to put master on here, as it is the 2nd binder param

    with requests.get(str(os.environ["BINDER_ADDR"])+'/build/git/'+gitlab_url+"/master", stream=True) as response:
        client = sseclient.SSEClient(response)
        for event in client.events():
            data = json.loads(event.data)

            if(data["phase"] == 'failed'):
                logger.warning("failure launching binder for manuscript "+ str(manuscript.id) + ": " + str(event.__dict__))
            else:
                logger.debug("launching binder for manuscript "+ str(manuscript.id) + ": " + str(event.__dict__))
            
            if(data["phase"] == 'ready'):
                url = data['url']
                token = data['token']
                print(url)
                print(token)

                return url + "?token=" + token


        raise Http404() #if we didn't return

            #print(event.__dict__)
            

            #If phase is ready, get url and token, construct url and pass back
            #If phase is error (or eventstream errors?) 404 for now, and do something smarter later?

            #... eventually we need to pipe this info into the browser 
