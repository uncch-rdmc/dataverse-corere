import git
from django.conf import settings

def create_repo(manuscript):
    repo = git.Repo.init(get_repo_path(manuscript), mkdir=True)
    repo.index.commit("initial commit")

def create_submission_branch(submission):
    repo = git.Repo(get_repo_path(submission.manuscript))
    repo.create_head('Submission_' + str(submission.version_id))

#TODO: How do we even get files from previous releases? Something like: https://stackoverflow.com/questions/7856416/
def get_repo_files(manuscript):
    repo = git.Repo(get_repo_path(manuscript))
    return helper_list_paths(repo.head.commit.tree, get_repo_path(manuscript), repo_name=get_repo_name(manuscript))

def store_file(manuscript, file):
    path = get_repo_path(manuscript)
    repo = git.Repo(path)
    with open(path + file.name, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    repo.index.add(file.name)
    repo.index.commit("store file: " + file.name)

#Use slug to get repo id
def get_repo_name(manuscript):
    return str(manuscript.id) + " - " + manuscript.slug

def get_repo_path(manuscript):
    return settings.GIT_ROOT+"/" + get_repo_name(manuscript) + "/"

#repo_name is required if relative
def helper_list_paths(root_tree, path, repo_name=None, relative=True):
    for blob in root_tree.blobs:
        if(relative):
            yield path.split(repo_name + "/")[1] + blob.name
        else:
            yield path + blob.name
    for tree in root_tree.trees:
        yield from helper_list_paths(tree, path + "/" + tree.name)