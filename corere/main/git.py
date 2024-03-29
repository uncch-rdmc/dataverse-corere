import git, os, hashlib, logging, io, tempfile, shutil
from django.conf import settings
from django.http import Http404, HttpResponse
from corere.main import models as m
from django.db.models import Max

logger = logging.getLogger(__name__)

# What actually makes something a "helper" here?


def create_manuscript_repo(manuscript):
    repo_path = get_manuscript_repo_path(manuscript)
    repo = git.Repo.init(repo_path, mkdir=True)
    files_path = get_manuscript_files_path(manuscript)
    os.makedirs(files_path, exist_ok=True)
    repo.index.commit("initial commit")


def create_submission_repo(manuscript):
    repo_path = get_submission_repo_path(manuscript)
    repo = git.Repo.init(repo_path, mkdir=True)
    files_path = get_submission_files_path(manuscript)
    os.makedirs(files_path, exist_ok=True)
    repo.index.commit("initial commit")
    # repo.create_head("master")


# #Maybe unused
# def get_manuscript_files_list(manuscript):
#     return _get_files_list(manuscript, get_manuscript_files_path(manuscript))

# #Only used for submission deleteallfiles
# def get_submission_files_list(manuscript):
#     print(get_submission_files_path(manuscript))
#     return _get_files_list(manuscript, get_submission_files_path(manuscript))

# #Only used for get_submission_files_list which is only used for deleteallfiles
# def _get_files_list(manuscript, path):
#     try:
#         print("huh")
#         repo = git.Repo(path+"..")
#         print(repo.__dict__)
#         if 'head' in repo.__dict__: #TODO: This doesn't work currently on the 1st submission because there is no head because we did not make a branch
#             return helper_list_paths(repo.head.commit.tree[0], path, path)
#         else:
#             print("NO COMMITS")
#             yield from () #If no head (e.g. no commits) return empty list
#         #TODO: We may want to handle having a head but no files
#     except git.exc.NoSuchPathError:
#         raise Http404()

# returns md5 of file
def store_manuscript_file(manuscript, file, subdir):
    repo_path = get_manuscript_repo_path(manuscript)
    files_folder = get_manuscript_files_path(manuscript, relative=True)
    return _store_file(repo_path, files_folder + subdir, file)


# returns md5 of file
def store_submission_file(manuscript, file, subdir):
    repo_path = get_submission_repo_path(manuscript)
    files_folder = get_submission_files_path(manuscript, relative=True)
    return _store_file(repo_path, files_folder + subdir, file)


# TODO-REPO: repo_path variable name here is incorrect. Probably other places too

# store file to filesystem, create commit for file
# returns md5 of file
def _store_file(repo_path, subdir, file):
    repo = git.Repo(repo_path)
    full_path = repo_path + subdir

    os.makedirs(full_path, exist_ok=True)
    hash_md5 = hashlib.md5()
    with open(full_path + file.name, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)
            hash_md5.update(chunk)
    repo.index.add(full_path + file.name)
    repo.index.commit("store file: " + full_path + file.name)
    return hash_md5.hexdigest()


def rename_manuscript_files(manuscript, files_dict_list):
    repo_path = get_manuscript_repo_path(manuscript)
    files_folder = get_manuscript_files_path(manuscript, relative=True)
    return _rename_files(repo_path, files_folder, files_dict_list)


def rename_submission_files(manuscript, files_dict_list):
    repo_path = get_submission_repo_path(manuscript)
    files_folder = get_submission_files_path(manuscript, relative=True)
    return _rename_files(repo_path, files_folder, files_dict_list)

def _rename_files(repo_path, files_folder, files_dict_list):
    repo = git.Repo(repo_path)

    for d in files_dict_list:
        old_path = files_folder + d.get("old")
        new_path = files_folder + d.get("new")

        if os.path.exists(repo_path + new_path):
            logger.warning(
                "Error renaming files, new path already exists. Repo path: "
                + repo_path
                + " . Current file old path: "
                + old_path
                + " . New path: "
                + new_path
                + " ."
            )
            return False
        try:
            os.renames(repo_path + old_path, repo_path + new_path)
            repo.index.add(repo_path + new_path)
            repo.index.remove(repo_path + old_path)
            repo.index.commit("File " + repo_path + old_path + " renamed to " + repo_path + new_path)
        except Exception as e:
            logger.error(
                "Error renaming files. Cause uncertain. Repo path: "
                + repo_path
                + " . Current file old path: "
                + old_path
                + " . New path: "
                + new_path
                + " . Error "
                + str(e)
            )
            return False

        return True


def delete_manuscript_file(manuscript, file_path):
    repo_path = get_manuscript_repo_path(manuscript)
    files_folder = get_manuscript_files_path(manuscript, relative=True)
    # if(not file_path == '/.git'):
    _delete_file(repo_path, repo_path + files_folder + file_path)

    # We recreate our "inside the repo" directory incase our delete recursively deleted it
    files_path = get_manuscript_files_path(manuscript)
    os.makedirs(files_path, exist_ok=True)


def delete_submission_file(manuscript, file_path):
    repo_path = get_submission_repo_path(manuscript)
    files_folder = get_submission_files_path(manuscript, relative=True)
    # if(not file_path == '/.git'):
    _delete_file(repo_path, repo_path + files_folder + file_path)

    # We recreate our "inside the repo" directory incase our delete recursively deleted it
    # TODO: This is likely slow when called many times (e.g. old delete all). If we have performance issues we should only call it once at the end of many deletes
    files_path = get_submission_files_path(manuscript)
    os.makedirs(files_path, exist_ok=True)


def delete_all_submission_files(manuscript):
    submission_files_path = get_submission_files_path(manuscript)
    shutil.rmtree(submission_files_path)
    os.makedirs(submission_files_path)
    repo = git.Repo(get_submission_repo_path(manuscript))
    try:
        repo.index.remove(submission_files_path, r=True)
    except Exception as e:
        if not str(e).endswith("did not match any files'"):
            # We catch the error of there being no files to delete
            raise e
    repo.index.commit("delete all submission files")


# delete file from filesystem, create commit for file
# TODO: This currently will delete the
def _delete_file(repo_path, file_full_path):
    repo = git.Repo(repo_path)
    if repo_path in os.path.realpath(file_full_path):
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
            file_full_folder = file_full_path.rsplit("/", 1)[0]
            try:
                os.removedirs(file_full_folder)  # deletes empty folders recursively. Will never delete repo_path as there is a git folder
            except OSError:
                pass  # If file_full_folder has other files, removedirs will error and fail, as expected
        else:
            logger.error("Attempted to delete file where path did not exist. Path provided: " + file_full_path)
            raise Http404()
    else:
        logger.error("Attempted to delete file above the repo path. Possibly a hack attempt. Path: " + file_full_path)
        raise Http404()

    repo.index.remove(file_full_path)
    repo.index.commit("delete file: " + file_full_path)


def get_manuscript_file(manuscript, file_path, response=False):
    repo_path = get_manuscript_repo_path(manuscript)
    files_folder = get_manuscript_files_path(manuscript, relative=True)
    return _get_file(repo_path, files_folder, file_path, "master", response)


def get_submission_file(submission, file_path, response=False):
    repo_path = get_submission_repo_path(submission.manuscript)
    files_folder = get_submission_files_path(submission.manuscript, relative=True)

    # We have to check whether our submission is the latest submission. If its latest, use master, otherwise use branch name
    max_version_id = submission.manuscript.get_max_submission_version_id()
    if submission.version_id == max_version_id:
        branch_name = "master"
    else:
        branch_name = helper_get_submission_branch_name(submission)
    return _get_file(repo_path, files_folder, file_path, branch_name, response)


def _get_file(repo_path, files_folder, file_path, branch_name, response):
    repo = git.Repo(repo_path)
    branch_commit = repo.commit(branch_name)
    if file_path[0] == "/":
        file_path = file_path[1:]  # [1:] removes leading slash. Could be made more robust
    file_path = files_folder + file_path
    file = branch_commit.tree / file_path

    if response:
        with io.BytesIO(file.data_stream.read()) as f:
            response = HttpResponse(f.read(), content_type=file.mime_type)
            response["Content-Disposition"] = 'attachment; filename="' + file.name + '"'
            return response
    else:
        return file


def download_all_submission_files(submission):
    max_version_id = submission.manuscript.get_max_submission_version_id()
    if submission.version_id == max_version_id:
        branch_name = "master"
    else:
        branch_name = helper_get_submission_branch_name(submission)

    repo_path = get_submission_repo_path(submission.manuscript)
    repo = git.Repo(repo_path)

    tempf = tempfile.TemporaryFile()
    repo.archive(tempf, treeish=branch_name)
    tempf.seek(0)  # you have to return to the start of the temporaryfile after writing to it

    response = HttpResponse(tempf.read(), content_type="application/zip")  # temp.mime_type)
    response["Content-Disposition"] = 'attachment; filename="' + submission.manuscript.slug + "_-_submission_" + str(submission.version_id) + '.zip"'
    return response


def download_all_manuscript_files(manuscript):
    branch_name = "master"
    repo_path = get_manuscript_repo_path(manuscript)
    repo = git.Repo(repo_path)

    tempf = tempfile.TemporaryFile()
    repo.archive(tempf, treeish=branch_name)
    tempf.seek(0)  # you have to return to the start of the temporaryfile after writing to it

    response = HttpResponse(tempf.read(), content_type="application/zip")  # temp.mime_type)
    response["Content-Disposition"] = 'attachment; filename="' + manuscript.slug + '_-_manuscript.zip"'
    return response


# def get_manuscript_repo_name(manuscript):
#     return str(manuscript.id) + "_-_manuscript_-_" + manuscript.slug

# def get_submission_repo_name(manuscript):
#     return str(manuscript.id) + "_-_submission_-_" + manuscript.slug


### The repo contains a sub-folder containing all the files. This is half to support downloading zips with a root folder

#TODO: Maybe rename these path endpoints to communicate they are getting the system path not the relative path in the code folder
def get_manuscript_repo_path(manuscript):
    return settings.GIT_ROOT + "/" + str(manuscript.id) + "_-_manuscript_-_" + manuscript.slug + "/"


def get_manuscript_files_path(manuscript, relative=False):
    rel_path = manuscript.slug + "_-_manuscript/"
    if relative:
        return rel_path
    else:
        return get_manuscript_repo_path(manuscript) + rel_path


def get_submission_repo_path(manuscript):
    return settings.GIT_ROOT + "/" + str(manuscript.id) + "_-_submission_-_" + manuscript.slug + "/"


def get_submission_files_path(manuscript, relative=False):
    rel_path = manuscript.slug + "_-_submission/"
    if relative:
        return rel_path
    else:
        return get_submission_repo_path(manuscript) + rel_path


def create_submission_branch(submission):
    repo = git.Repo(get_submission_repo_path(submission.manuscript))
    repo.create_head(helper_get_submission_branch_name(submission))


# Lists the paths of all the files. Used only to delete_all currently
# When initially called, repo_path and rel_path should be the same.
# TODO: This actually returns a generator, we should probably name it differently or switch it to a list
# def helper_list_paths(root_tree, repo_path, rel_path):
#     for blob in root_tree.blobs:
#         #Split off the system path from the return.
#         yield (rel_path.split(repo_path, 1)[1] + '/' + blob.name)#[1:] #commented code would remove leading slash
#     for tree in root_tree.trees:
#         yield from (helper_list_paths(tree, repo_path, rel_path + '/' + tree.name)) #recursive

# Note: Submission branches are only created when the submission is completed. This will not tell you whether your submission has been completed.
def helper_get_submission_branch_name(submission):
    return "Submission_" + str(submission.version_id)
