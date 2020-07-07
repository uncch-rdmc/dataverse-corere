from django.contrib.messages import constants as messages

GROUP_ROLE_EDITOR = "Role Editor"
GROUP_ROLE_AUTHOR = "Role Author"
GROUP_ROLE_VERIFIER = "Role Verifier"
GROUP_ROLE_CURATOR = "Role Curator"
GROUP_MANUSCRIPT_EDITOR_PREFIX = "Editor Manuscript"
GROUP_MANUSCRIPT_AUTHOR_PREFIX = "Author Manuscript"
GROUP_MANUSCRIPT_VERIFIER_PREFIX = "Verifier Manuscript"
GROUP_MANUSCRIPT_CURATOR_PREFIX = "Curator Manuscript"

def get_roles():
    return [GROUP_ROLE_EDITOR, GROUP_ROLE_AUTHOR, GROUP_ROLE_VERIFIER, GROUP_ROLE_CURATOR]