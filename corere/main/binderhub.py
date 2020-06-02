import requests, logging, os, urllib
logger = logging.getLogger(__name__)  

def binder_build_load(manuscript):
    print(os.environ["BINDER_ADDR"])
    #MAD: This doesn't work with private repos, but I've set 103 to public
    #git@192.168.50.125:root/103-test-gitlab-submissions.git
    #gitlab_url = '192.168.50.125' + "/root/"+helper_get_gitlab_project_name(manuscript.id, manuscript.title, True)

    #gitlab_url = "192.168.50.125:root/103-test-gitlab-submissions.git" #CLOSER

    # A good url from the prototype
    #http://10.96.177.79/build/git/http%3A%2F%2F192.168.50.125%2Froot%2Ftest/0bb86fe3b762e58804a24aaf64d93a49bb4408f5
    # My "latest" url, sad
    #http://10.96.177.79/build/git/http://192.168.50.125/root/103%20-%20Test%20Gitlab%20-%20Submissions/e5c6f657cc8e13fdd5cafa1888b1df395a0d893c

    #!!! STARTS and works. looks like a major problem was the / on the /root/
    #http://10.96.177.79/build/git/http%3A%2F%2F192.168.50.125%2Froot%2F103-test-gitlab-submissions/master

    #current one we are generating, fails
    #http://10.96.177.79/build/git/http%3A%2F%2F192.168.50.125%2Froot%2F112_-_the_best_new_manuscript_5_-_Submissions/master
    #we need it to be:
    #http://10.96.177.79/build/git/http%3A%2F%2F192.168.50.125%2Froot%2F112_-_the_best_new_manuscript_5_-_Submissions/master


    # 2 problems:
    # - GitLab does weird things creating a url with the title. I should not provide any spaces
    # - I need to get the right sha, unsure if I'm doing that?
    #   - I may not actually need to, I can just say the branch name?

    #I need the commit sha
    #gitlab_url = "192.168.50.125/root/103-test-gitlab-submissions.git"

    #We don't need the sha, we can just specify the branch (master). This may have not gotten the right sha anyways
    #latest_sha = gitlab_get_latest_commit_sha(manuscript.gitlab_submissions_id)

    #THE REAL ONE:
    gitlab_url = urllib.parse.quote( (os.environ["GIT_LAB_URL"] + "/root/"+manuscript.gitlab_submissions_path), safe='') #true for submissions repo, the one we build off

    #yes, we have to put master on here, as it is the 2nd binder param
    response = requests.get(str(os.environ["BINDER_ADDR"])+'/build/git/'+gitlab_url+"/master")#+latest_sha)#+str(manuscript.gitlab_submissions_id)+'/master')#, auth=('user', 'pass'))
    return response

    #<url-escaped-namespace>/<unresolved_ref> (e.g. group%2Fproject%2Frepo/master)
