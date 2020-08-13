import gitlab, logging, os, re, random, string
from django.conf import settings
logger = logging.getLogger(__name__)  

#https://docs.gitlab.com/ee/api/users.html#user-creation
def gitlab_create_user(django_user):
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

#TODO: What is the output of this?
#TODO: I think this errors if there are no files in the repo? "tree not found"
def gitlab_repo_get_file_folder_list(repo_id):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return [{"path":"fakefile1.png"},{"path":"fakefile2.png"}]
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        try:
            repo_tree = gl.projects.get(repo_id).repository_tree(recursive=True)
        except gitlab.GitlabGetError:
            logger.warning("Unable to access gitlab for gitlab_repo_get_file_folder_list")
            repo_tree = []
        logger.debug(repo_tree)
        return repo_tree
        
# Maybe need to allow branch specification?
def gitlab_delete_file(repo_id, file_path):
    if(hasattr(settings, 'DISABLE_GIT') and settings.DISABLE_GIT):
        return
    else:
        gl = gitlab.Gitlab(os.environ["GIT_LAB_URL"], private_token=os.environ["GIT_PRIVATE_ADMIN_TOKEN"])
        gl.enable_debug()

        gl_project = gl.projects.get(repo_id)
        gl_project.files.delete(file_path=file_path, commit_message='Delete file', branch='master')

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
#
# https://docs.gitlab.com/ee/api/users.html#create-an-impersonation-token
def gitlab_generate_impersonation_token(self, token_user, timeout=1):
    pass

#Does not actually access gitlab. One place that defines how we name things. Important for urls etc
#NOTE: Don't use this after creation, as changes in corere project name do not propigate to gitlab
def _helper_generate_gitlab_project_name(id, title, is_sub):
    pro_name = str(id) + " - " + re.sub('[^a-zA-Z0-9_. -]' ,'' ,title)
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