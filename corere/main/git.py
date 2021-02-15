import git, os, hashlib, logging, io, tempfile
from django.conf import settings
from django.http import Http404, HttpResponse
from corere.main import models as m
from django.db.models import Max
logger = logging.getLogger(__name__)

#What actually makes something a "helper" here?

def create_manuscript_repo(manuscript):
    _create_repo(manuscript, get_manuscript_repo_path(manuscript))

def create_submission_repo(manuscript):
    _create_repo(manuscript, get_submission_repo_path(manuscript))

def _create_repo(manuscript, path):
    repo = git.Repo.init(path, mkdir=True)
    repo.index.commit("initial commit")


def get_manuscript_files_list(manuscript):
    return _get_files_list(manuscript, get_manuscript_repo_path(manuscript), get_manuscript_repo_name(manuscript))

#TODO: How do we even get files from previous releases? Something like: https://stackoverflow.com/questions/7856416/
def get_submission_files_list(manuscript):
    return _get_files_list(manuscript, get_submission_repo_path(manuscript), get_submission_repo_name(manuscript))

def _get_files_list(manuscript, path, repo_name):
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

#store file to filesystem, create commit for file
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

def delete_manuscript_file(manuscript, file_path):
    repo_path = get_manuscript_repo_path(manuscript)
    _delete_file(repo_path, repo_path + file_path)

def delete_submission_file(manuscript, file_path):
    repo_path = get_submission_repo_path(manuscript)
    _delete_file(repo_path, repo_path + file_path)

#delete file from filesystem, create commit for file
def _delete_file(repo_path, file_full_path):
    repo = git.Repo(repo_path)
    if os.path.exists(file_full_path):
        os.remove(file_full_path)
    else:
        logger.error("Attempted to delete file where path did not exist. Path provided: " + file_full_path)
        raise Http404()
    repo.index.remove(file_full_path)
    repo.index.commit("delete file: " + file_full_path)


def download_manuscript_file(manuscript, file_path):
    repo_path = get_manuscript_repo_path(manuscript)
    return _download_file(repo_path, file_path, 'master')

def download_submission_file(submission, file_path):
    print("DOWNLOAD SUB")
    repo_path = get_submission_repo_path(submission.manuscript)

    #We have to check whether our submission is the latest submission. If its latest, use master, otherwise use branch name
    max_version_id = m.Submission.objects.filter(manuscript=submission.manuscript).aggregate(Max('version_id'))['version_id__max']
    if(submission.version_id == max_version_id):
        branch_name = 'master'
    else:
        branch_name = helper_get_submission_branch_name(submission)
    return _download_file(repo_path, file_path, branch_name)

def _download_file(repo_path, file_path, branch_name):
    repo = git.Repo(repo_path)
    branch_commit = repo.commit(branch_name)
    if(file_path[0] == '/'):
        file_path = file_path[1:]
    file = branch_commit.tree / file_path #[1:] removes leading slash. Could be made more robust

    with io.BytesIO(file.data_stream.read()) as f:
        response = HttpResponse(f.read(), content_type=file.mime_type)
        response['Content-Disposition'] = 'attachment; filename="'+ file.name +'"'
        return response

def download_all_submission_files(submission):
    max_version_id = m.Submission.objects.filter(manuscript=submission.manuscript).aggregate(Max('version_id'))['version_id__max']
    if(submission.version_id == max_version_id):
        branch_name = 'master'
    else:
        branch_name = helper_get_submission_branch_name(submission)

    repo_path = get_submission_repo_path(submission.manuscript)
    repo = git.Repo(repo_path)

    tempf = tempfile.TemporaryFile()
    repo.archive(tempf, treeish=branch_name)
    tempf.seek(0) #you have to return to the start of the temporaryfile after writing to it

    #print(str(os.fstat(tempf.fileno()).st_size))

    
    
    response = HttpResponse(tempf.read(), content_type='application/zip')#temp.mime_type)
    response['Content-Disposition'] = 'attachment; filename="'+submission.manuscript.slug + '_-_submission_' + str(submission.version_id) + '.zip"'
    return response



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
        #Split off the system path from the return. 
        yield (rel_path.split(repo_path, 1)[1] + '/' + blob.name)#[1:] #commented code would remove leading slash
    for tree in root_tree.trees:
        yield from (helper_list_paths(tree, repo_path, rel_path + '/' + tree.name)) #recursive

#Note: Submission branches are only created when the submission is completed. This will not tell you whether your submission has been completed.
def helper_get_submission_branch_name(submission):
    return 'Submission_' + str(submission.version_id)