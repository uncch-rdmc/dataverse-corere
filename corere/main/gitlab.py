import gitlab, logging, os, re, random, string, time
from corere.main import models as m #TODO: Switch to GitlabFile
from django.conf import settings
logger = logging.getLogger(__name__)  

#TODO: I should be referencing settings here, not environ directly!

#https://docs.gitlab.com/ee/api/users.html#user-creation
def gitlab_create_user(django_user, is_admin=False):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        #gl.enable_debug()
        gitlab_user = gl.users.create({
                            'email': "fakeemail"+str(django_user.id)+"@odum.unc.edu", #we set this wrong as a security measure
                            'force_random_password': True,
                            'username': django_user.username,
                            'name': django_user.email, #We use email becasue when we create the user there is no username info.
                            'external':True, 
                            'private_profile':True , 
                            'skip_confirmation':True,
                            'admin': is_admin,
                            #TODO: Once this issue is fixed, remove our random password generation. https://gitlab.com/gitlab-org/gitlab/-/issues/25802
                            'password' : ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(20))})
        django_user.gitlab_id = gitlab_user.id                   
        django_user.save()

#TODO: Add update user command to update on users.account_user_details() changes
def gitlab_update_user(django_user):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        #gl.enable_debug()
        logger.debug(django_user.__dict__)

        #TODO: is this efficient? I feel like it may be doing multiple calls under the hood...

        gl_user = gl.users.get(django_user.gitlab_id)
        if(not django_user.first_name or not django_user.last_name):
            gl_user.name = django_user.first_name + " " + django_user.last_name
        else: #this case should never hit on update, but just in case
            gl_user.name = django_user.email
        gl_user.username = django_user.username
        gl_user.save()

# https://docs.gitlab.com/ee/api/members.html#add-a-member-to-a-group-or-project
# https://docs.gitlab.com/ee/api/members.html top has info on access levels
# http://vlabs.iitb.ac.in/gitlab/help/user/permissions.md useful about access levels
def gitlab_add_user_to_repo(django_user, repo_id):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        #gl.enable_debug()
        gl_project = gl.projects.get(repo_id)
        #TODO: what happens if a member already exists?
        gl_project.members.create({'user_id': django_user.gitlab_id, 'access_level':
                                    gitlab.DEVELOPER_ACCESS})

def gitlab_remove_user_from_repo(django_user, repo_id):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        gl_project = gl.projects.get(repo_id)
        gl_project.members.delete(django_user.gitlab_id)

#For now, all created projects are public, until we configure binderhub for private self-hosted gitlab repos
def gitlab_create_manuscript_repo(manuscript):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        name = _helper_generate_gitlab_project_name(manuscript.id, manuscript.title, False)
        path = _helper_generate_gitlab_project_path(manuscript.id, manuscript.title, False)
        gitlab_project = gl.projects.create({'name': name, 'path': path, 'visibility': 'public'})
        manuscript.gitlab_manuscript_id = gitlab_project.id
        manuscript.gitlab_manuscript_path = path
        manuscript.save()

#For now, all created projects are public, until we configure binderhub for private self-hosted gitlab repos
def gitlab_create_submissions_repo(manuscript):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        name = _helper_generate_gitlab_project_name(manuscript.id, manuscript.title, True)
        path = _helper_generate_gitlab_project_path(manuscript.id, manuscript.title, True)
        gitlab_project = gl.projects.create({'name': name, 'path': path, 'visibility': 'public'})
        manuscript.gitlab_submissions_id = gitlab_project.id
        manuscript.gitlab_submissions_path = path
        manuscript.save()

def gitlab_create_submission_branch(manuscript, repo_id, branch, ref_branch):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        gl_project = gl.projects.get(repo_id)
        # print(branch)
        # print(ref_branch)
        # print(repo_id)

        branch = gl_project.branches.create({'branch': branch, 'ref': ref_branch})

def gitlab_repo_get_commit_list(repo_id, branch):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return []
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        try:
            commits = gl.projects.get(repo_id).commits
            print(commits)
            return gl.projects.get(repo_id).commits.list(all=True, query_parameters={'ref_name': branch})
        except gitlab.GitlabGetError:
            logger.warning("Unable to access gitlab for gitlab_repo_get_file_folder_list")
            raise

#TODO: I think this errors if there are no files in the repo? "tree not found"
def gitlab_repo_get_file_folder_list(repo_id, branch):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return [{"path":"fakefile1.png"},{"path":"fakefile2.png"}]
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        try:
            repo_tree_full = gl.projects.get(repo_id).repository_tree(recursive=True, ref=branch)
            repo_tree = [item for item in repo_tree_full if item['type'] != 'tree']
        except gitlab.GitlabGetError as e:
            if(str(e) == "404: 404 Tree Not Found"):
                return [] #when the repo is newly created there is no branch so it errors
            else:
                logger.error("Unable to access gitlab for gitlab_repo_get_file_folder_list")
                raise
        logger.debug(repo_tree)
        return repo_tree

#Gets info about a file without having to get the file itself
#blame headers is the same as file headers
#I just implemented it with blame because there was other useful looking info not in the header (which we ended up not using)
def gitlab_get_file_blame_headers(repo_id, branch, file_path):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        #TODO: Change this to something else? Or Remove it?
        return [{"path":"fakefile1.png"},{"path":"fakefile2.png"}]
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        return gl.projects.get(repo_id).files.blame_head(file_path=file_path, ref=branch)
    #b = project.files.blame(file_path='README.rst', ref='master')

# For each new file: use path to get blame headers, use blame headers to get commit, use commit to get date
#   - There's also a bunch of other data in each check we need

#TODO: Investigate getting all current and previous submission GitlabFiles in one query https://stackoverflow.com/questions/35314346/performance-optimization-on-django-update-or-create
#TODO: Name of function could be better
#TODO: Can we pass in the current dict list as we already got it once outside the place this is "normally" called?
def helper_populate_gitlab_files_submission(repo_id, submission):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    #TODO: switch this to use helper_get_submission_branch_name and fix its calls to use version

    cur_branch = "submission_" + str(submission.version_id)
    gl_repo_list = gitlab_repo_get_file_folder_list(repo_id, cur_branch)
    cur_sub_files = m.GitlabFile.objects.filter(parent_submission=submission)
    #These have been moved outside for efficiency, though I'm not sure its actually caching
    if(submission.version_id-1 > 0):
        prev_submission = m.Submission.objects.get(manuscript=submission.manuscript, version_id=submission.version_id-1)
        prev_sub_files = m.GitlabFile.objects.filter(parent_submission=prev_submission.id)

    for item in gl_repo_list:

        ask_gitlab = False
        try:
            cur_file = cur_sub_files.get(gitlab_path=item['path'])
        except m.GitlabFile.DoesNotExist:
            cur_file = m.GitlabFile()
            cur_file.parent_submission = submission
            cur_file.gitlab_path = item["path"]
            ask_gitlab = True

        #path same but file or git metadata changed
        #would be better if we could just check on file, but that's how it goes
        if(ask_gitlab or cur_file.gitlab_blob_id != item["id"]): #TODO: sha1 will never be item id, as sha1 is currently commit id!!!!!
            commit = None
            if('gl_commit_list' not in locals()):
                gl_commit_list = gitlab_repo_get_commit_list(repo_id, cur_branch)
                print("GL COMMIT LIST")
                print(gl_commit_list)
            
            gl_blame_head_resp = gitlab_get_file_blame_headers( repo_id , cur_branch, cur_file.gitlab_path) #(repo_id, branch, file_path):
            print(gl_blame_head_resp.__dict__)
            cur_file.gitlab_sha256 = gl_blame_head_resp.__dict__.get('headers').get('X-Gitlab-Content-Sha256')
            cur_file.gitlab_size = gl_blame_head_resp.__dict__.get('headers').get('X-Gitlab-Size')
            commit_id = gl_blame_head_resp.__dict__.get('headers').get('X-Gitlab-Last-Commit-Id') #TODO: It shouldn't be commit-id?
            
            #TODO: We could use short id instead for some efficiency: https://stackoverflow.com/a/43666212/1017302
            
            for c in gl_commit_list:
                if(c.id == commit_id):
                    commit = c
                    print("COMMIT")
                    print(commit.id)
                    break
            
            cur_file.gitlab_date = commit.authored_date
            cur_file.gitlab_blob_id = item['id']

        if(submission.version_id-1 > 0):
            try:
                prev_file = prev_sub_files.get(gitlab_path=item['path'])
                cur_file.tag = prev_file.tag
                cur_file.description = prev_file.description
            except m.GitlabFile.DoesNotExist:
                #set fields from item? seems wrong?
                pass

        cur_file.save()

        #print(cur_file.__dict__)

    #TODO: maybe combine this with the previous iteration for some additional efficiency
    
    print("gl_repo_list")
    print(gl_repo_list)
    print("==============")
    for f in cur_sub_files:
        print("FILE")
        print(f.__dict__)
        print("==============")
        exists = False
        for item in gl_repo_list:
            print("FILE IN GITLAB")
            print(item)
            print("==============")
            if(f.gitlab_blob_id == item["id"]):
                exists = True
                break   
        if (exists == False):
            print("DELETE")
            print("==============")
            print("==============")
            #print(f.__dict__)
            #Our file for the current submission was deleted in gitlab, so delete in CoReRe
            f.delete()


        #If path + current_branch exists, continue (skip current loop iteration)
        #If path + previous_branch exists, create new object with data from previous one
        #Else, create completely new object
        #... In what case do I query gitlab for more info? When sha1 doesn't match?

# Only allows deleting from the "latest" branch (for submissions, manuscript is always master)
def gitlab_delete_file(obj_type, obj, repo_id, file_path):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        gl.enable_debug()
        gl_project = gl.projects.get(repo_id)

        if(obj_type == "manuscript"):
            gl_project.files.delete(file_path=file_path, commit_message='Delete file', branch='master')
        elif(obj_type == "submission"):
            gl_project.files.delete(file_path=file_path, commit_message='Delete file', branch=helper_get_submission_branch_name(obj.manuscript))
        else:
            raise ValueError

#Delete the existing branch and make a new one off master (which has nothing?)
#This code only works for submissions
#How do we get branch name from repo id?
def gitlab_submission_delete_all_files(submission):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return

    current_branch = helper_get_submission_branch_name(submission.manuscript)
    gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
    gl_project = gl.projects.get(submission.manuscript.gitlab_submissions_id)
    gl_project.branches.delete(current_branch)
    gl_project.branches.create({'branch': current_branch, 'ref': 'master'})

#This is unused as we just specify master. It may have never gotten the latest/correct sha
# def gitlab_get_latest_commit_sha(repo_id):
#     gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
#     gl_project = gl.projects.get(repo_id)
#     print(gl_project.repository_tree(ref='master')[0])
#     return gl_project.repository_tree(ref='master')[0].get('id')



# There is no api for this, impersonation tokens generated by the admin must be used
# def gitlab_generate_access_token(user, timeout=1):
#     pass

# This endpoint is so the admin can generate an access token as a different user
# This will be used by the end-user as well, as there is no way for admin to generate a normal access token via API (in April 2020)
# The difference between an impersonation token and a normal access token is nothing for our user cases
# The only difference is that the user can't see impersonation tokens via the UI, but CoReRe users should never see the UI anyways

# https://docs.gitlab.com/ee/api/users.html#create-an-impersonation-token
def gitlab_generate_impersonation_token(self, token_user, timeout=1):
    pass

#----- Used by gitlabdeleteall management command
def gitlab_delete_all_projects():
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
    projects = gl.projects.list()
    print(len(projects))
    for project in projects:
        project.delete()
        time.sleep(1)
    return len(projects)

def gitlab_delete_all_users_besides_root():
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
    users = gl.users.list()
    print(len(users))
    for user in users:
        if(user.username != "root"):
            user.delete()   
            time.sleep(1)
    return len(users)
    

#TODO: Find a better way to clarify that some helpers I expect to be called outside and some not.
#Some say its not best practice to have these helpers in here, but I want all the gitlab functions clustered...

#Does not actually access gitlab. One place that defines how we name things. Important for urls etc
#NOTE: Don't use this after creation, as changes in corere project name do not propigate to gitlab
def _helper_generate_gitlab_project_name(manuscript_id, title, is_sub):
    pro_name = str(manuscript_id) + " - " + re.sub('[^a-zA-Z0-9_. -]' ,'' ,title)
    if(is_sub):
        pro_name += " - Submissions"
    else:
        pro_name += " - Manuscript"
    return pro_name

#Gitlab does not allow ' ' in paths. If you provide it a name without a path for creation, it replaces ' ' with '-', but we want '_'
#NOTE: Don't use this after creation, as changes in corere project path do not propigate to gitlab (and are unable to)
def _helper_generate_gitlab_project_path(id, title, is_sub):
    pro_name = _helper_generate_gitlab_project_name(id, title, is_sub)
    pro_path = re.sub(' ' ,'_' ,pro_name)

    return pro_path

#TODO: This should probably use submission.version instead of doing count
def helper_get_submission_branch_name(manuscript):
    if(manuscript.manuscript_submissions.count() == 0):
        raise ValueError
    return "submission_" + str(manuscript.manuscript_submissions.count())