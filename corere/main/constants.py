from django.contrib.messages import constants as messages

GROUP_ROLE_EDITOR = "Role Editor"
GROUP_ROLE_AUTHOR = "Role Author"
GROUP_ROLE_VERIFIER = "Role Verifier"
GROUP_ROLE_CURATOR = "Role Curator"
GROUP_MANUSCRIPT_EDITOR_PREFIX = "Editor Manuscript"
GROUP_MANUSCRIPT_AUTHOR_PREFIX = "Author Manuscript"
GROUP_MANUSCRIPT_VERIFIER_PREFIX = "Verifier Manuscript"
GROUP_MANUSCRIPT_CURATOR_PREFIX = "Curator Manuscript"
GROUP_MANUSCRIPT_ADMIN = "Corere Admin"  # Only used currently for Whole Tale group
GROUP_COMPLETED_SUFFIX = "Completed"

# TODO: This should be used throughout the code
def generate_group_name(group_prefix, manuscript):
    return f"{group_prefix} {manuscript.id}"


def get_roles():
    return [GROUP_ROLE_EDITOR, GROUP_ROLE_AUTHOR, GROUP_ROLE_VERIFIER, GROUP_ROLE_CURATOR]


def get_private_roles():
    return [GROUP_ROLE_VERIFIER, GROUP_ROLE_CURATOR]


# Manuscript perm strings
PERM_MANU_ADD_M = "add_manuscript"
PERM_MANU_CHANGE_M = "change_manuscript"
PERM_MANU_CHANGE_M_FILES = "change_manuscript_files"
PERM_MANU_DELETE_M = "delete_manuscript"
PERM_MANU_VIEW_M = "view_manuscript"
PERM_MANU_ADD_AUTHORS = "add_authors_on_manuscript"
PERM_MANU_REMOVE_AUTHORS = "remove_authors_on_manuscript"
PERM_MANU_MANAGE_EDITORS = "manage_editors_on_manuscript"
PERM_MANU_MANAGE_CURATORS = "manage_curators_on_manuscript"
PERM_MANU_MANAGE_VERIFIERS = "manage_verifiers_on_manuscript"
PERM_MANU_ADD_SUBMISSION = "add_submission_to_manuscript"
PERM_MANU_APPROVE = "approve_manuscript"
PERM_MANU_CURATE = "curate_manuscript"
PERM_MANU_VERIFY = "verify_manuscript"
PERM_MANU_NOTIFY = "notify_about_manuscript"

# Note perm strings
# PERM_NOTE_ADD_N = 'add_note'
PERM_NOTE_CHANGE_N = "change_note"
# PERM_NOTE_DELETE_N = 'delete_note'
PERM_NOTE_VIEW_N = "view_note"

# You need the perm path when checking non-object perms
def perm_path(perm):
    return "main." + perm


progress_list_manuscript = ["Create Manuscript", "Upload Files", "Invite Author"]
progress_list_container_submission = ["Update Manuscript", "Upload Files", "Run Code", "Add Submission Info"]
progress_list_external_submission = ["Update Manuscript", "Upload Files", "Add Submission Info"]
