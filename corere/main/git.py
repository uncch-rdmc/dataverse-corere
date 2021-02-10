import git, os, hashlib
from django.conf import settings
from django.http import Http404

#What actually makes something a "helper" here?


def create_manuscript_repo(manuscript):
    _create_repo(manuscript, get_manuscript_repo_path(manuscript))

def create_submission_repo(manuscript):
    _create_repo(manuscript, get_submission_repo_path(manuscript))

def _create_repo(manuscript, path):
    repo = git.Repo.init(path, mkdir=True)
    repo.index.commit("initial commit")


def get_manuscript_files(manuscript):
    return _get_files(manuscript, get_manuscript_repo_path(manuscript), get_manuscript_repo_name(manuscript))

#TODO: How do we even get files from previous releases? Something like: https://stackoverflow.com/questions/7856416/
def get_submission_files(manuscript):
    return _get_files(manuscript, get_submission_repo_path(manuscript), get_submission_repo_name(manuscript))

def _get_files(manuscript, path, repo_name):
    # print("Manuscript: " + str(manuscript))
    # print("Path: " + path)
    # print("Repo Name: " + repo_name)
    # print("============================")
    try:
        repo = git.Repo(path)
        return helper_list_paths(repo.head.commit.tree, path, path)
    except git.exc.NoSuchPathError:
        raise Http404()

#returns md5 of file
def store_manuscript_file(manuscript, file, subdir):
    repo_path = get_manuscript_repo_path(manuscript)
    return _store_file(repo_path, subdir, file)

#returns md5 of file
def store_submission_file(manuscript, file, subdir):
    repo_path = get_submission_repo_path(manuscript)
    return _store_file(repo_path, subdir, file)

#returns md5 of file
def _store_file(repo_path, subdir, file):
    repo = git.Repo(repo_path)
    full_path = repo_path + subdir
    os.makedirs(full_path, exist_ok=True)
    hash_md5 = hashlib.md5()
    with open(full_path + file.name, 'wb+') as destination:
        for chunk in file.chunks(): #use chunk_size=4096 if md5 doesn't work right
            destination.write(chunk)
            hash_md5.update(chunk)
    repo.index.add(full_path + file.name)
    repo.index.commit("store file: " + full_path + file.name)
    return hash_md5.hexdigest()



#Use slug to get repo id
def get_manuscript_repo_name(manuscript):
    return str(manuscript.id) + "_-_manuscript_-_" + manuscript.slug

def get_submission_repo_name(manuscript):
    return str(manuscript.id) + "_-_submission_-_" + manuscript.slug

def get_manuscript_repo_path(manuscript):
    return settings.GIT_ROOT+"/" + get_manuscript_repo_name(manuscript) + "/"

def get_submission_repo_path(manuscript):
    return settings.GIT_ROOT+"/" + get_submission_repo_name(manuscript) + "/"


def create_submission_branch(submission):
    repo = git.Repo(get_submission_repo_path(submission.manuscript))
    repo.create_head(helper_get_submission_branch_name(submission))

# When initially called, repo_path and rel_path should be the same.
def helper_list_paths(root_tree, repo_path, rel_path):
    for blob in root_tree.blobs:
        #Split off the system path from the return. Also the leading slash.
        yield (rel_path.split(repo_path, 1)[1] + '/' + blob.name)[1:]
    for tree in root_tree.trees:
        yield from (helper_list_paths(tree, repo_path, rel_path + '/' + tree.name)) #recursive

def helper_get_submission_branch_name(submission):
    return 'Submission_' + str(submission.version_id)