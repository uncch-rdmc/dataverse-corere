import json, unittest, mock

# import urllib.parse
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from corere.main.middleware import local
from corere.main import constants as c
from corere.main import models as m
from django.contrib.auth.models import Permission, Group
from rest_framework import status
from http import HTTPStatus
from django.core.management import call_command

# Fixture generation:
# - python3 manage.py dumpdata --indent=4 > corere/main/fixtures/manuscript_submission_states.json
#
# Fixture editing. You can load the fixture "normally" (and wipe out existing info by):
# - drop and create database with postgres (manage.py flush does not work)
# - python3 manage.py migrate
# - python3 manage.py loaddata manuscript_submission_states.json -e contenttypes

### NOTE: With all these tests, I tested all the important cases and some of the "this really shouldn't happen" cases. It is a bit vague though
# TODO: add tests with multiple of each role to assure only those assigned can do the action
# @unittest.skip("Incomplete")
class BaseTestWithFixture(TestCase):
    # Our many contants to make referncing our various cases easier
    # (Technically most "nouser" manuscripts actually have admin as an author)
    # Also note that even though we have files, delete does not actually delete a GitFile, it calls GitLab. So its kinda pointless to have these cases
    # Loading the submission page checks gitlab every time and deletes files if needed.

    # NOTE: Because editions were added later, the sub/cur/ver connected to them have less coverage.
    M_NEW_NOUSER = 1  # New manuscript no assigned users for any roles
    M_NEW_ALLUSER = 2  # New manuscript users assigned for all 4 roles
    M_NEW_AUTH_ED = 32  # Manuscript initial submission created and submitted, author/editor roles. Has files on sub
    M_NEW_AUTH = 33  # Manuscript initial submission created and submitted, author roles. Has files on sub
    M_B4_SUB1_ALLUSER = 3  # Manuscript awaiting initial submission, all 4 roles
    M_B4_SUB1_AUTHOR = 4  # Manuscript awaiting initial submission, only author assigned
    M_B4_SUB1_NOUSER = 5  # Manuscript awaiting initial submission, no roles
    M_DUR_SUB1_ALLUSER = 6  # Manuscript initial submission created but not submit, all 4 roles
    M_DUR_SUB1_NOUSER = 7  # Manuscript initial submission created but not submit, no roles
    M_DUR_SUB1_ALLUSER_F = 8  # Manuscript initial submission created but not submit, all roles. Has sub files
    M_DUR_SUB1_NOUSER_F = 9  # Manuscript initial submission created but not submit, no roles. Has sub files
    M_B4_ED1_ALLUSER = 10  # Manuscript awaiting initial edition, all 4 roles
    M_B4_ED1_NOUSER = 11  # Manuscript awaiting initial edition, no roles
    M_DUR_ED1_ALLUSER = 12  # Manuscript initial edition created but not submit, all 4 roles
    M_DUR_ED1_NOUSER = 13  # Manuscript initial edition created but not submit, no roles
    M_B4_CUR1_ALLUSER = 14  # Manuscript awaiting initial curation, all 4 roles
    M_B4_CUR1_AUTHOR_F = 15  # Manuscript initial submission created and submitted, author roles. Has files on sub
    M_B4_CUR1_NOUSER = 16  # Manuscript awaiting initial curation, no roles
    M_DUR_CUR1_ALLUSER = 17  # Manuscript initial curation created but not submit, all 4 roles
    M_DUR_CUR1_NOUSER = 18  # Manuscript initial curation created but not submit, no roles
    M_B4_VER1_ALLUSER = 19  # Manuscript awaiting initial verification, all 4 roles
    M_B4_VER1_NOUSER = 20  # Manuscript awaiting initial verification, no roles
    M_DUR_VER1_ALLUSER = 21  # Manuscript initial verification created but not submit, all 4 roles
    M_DUR_VER1_NOUSER = 22  # Manuscript initial verification created but not submit, no roles
    M_B4_REP1_ALLUSER = 23
    M_B4_REP1_NOUSER = 24
    M_B4_APPR1_ALLUSER = 25
    M_B4_APPR1_NOUSER = 26
    M_B4_SUB2_ALLUSER = 34  # Manuscript awaiting second submission, all 4 roles
    M_DONE_ALLUSER = 35  # Manuscript completed, all roles
    M_DONE_NOUSER = 36  # Manuscript completed, no roles

    S_DUR_SUB1_ALLUSER = 1
    S_DUR_SUB1_NOUSER = 2
    S_DUR_SUB1_ALLUSER_F = 3
    S_DUR_SUB1_NOUSER_F = 4
    S_B4_CUR1_ALLUSER = 9
    S_B4_CUR1_AUTHOR_F = 10
    S_B4_CUR1_NOUSER = 11
    S_DUR_CUR1_ALLUSER = 12
    S_DUR_CUR1_NOUSER = 13
    S_B4_VER1_ALLUSER = 14
    S_B4_VER1_NOUSER = 15
    S_DUR_VER1_ALLUSER = 16
    S_DUR_VER1_NOUSER = 17
    S_B4_SUB2_ALLUSER = 22
    S_DONE_ALLUSER = 28
    S_DONE_NOUSER = 29
    S_B4_ED1_ALLUSER = 5
    S_B4_ED1_NOUSER = 6
    S_DUR_ED1_ALLUSER = 7
    S_DUR_ED1_NOUSER = 8
    S_B4_REP1_ALLUSER = 18
    S_B4_REP1_NOUSER = 19
    S_B4_APPR1_ALLUSER = 20
    S_B4_APPR1_NOUSER = 21

    E_DUR_ED1_ALLUSER = 1
    E_DUR_ED1_NOUSER = 2
    E_B4_CUR1_ALLUSER = 3
    E_B4_CUR1_NOUSER = 5
    E_DUR_CUR1_ALLUSER = 6
    E_DUR_CUR1_NOUSER = 7
    E_B4_VER1_ALLUSER = 8
    E_B4_VER1_NOUSER = 9
    E_DUR_VER1_ALLUSER = 10
    E_DUR_VER1_NOUSER = 11
    E_B4_SUB2_ALLUSER = 19
    E_DONE_ALLUSER = 20
    E_DONE_NOUSER = 21
    E_B4_REP1_ALLUSER = 12
    E_B4_REP1_NOUSER = 13
    E_B4_APPR1_ALLUSER = 14
    E_B4_APPR1_NOUSER = 15

    C_DUR_CUR1_ALLUSER = 1
    C_DUR_CUR1_NOUSER = 2
    C_B4_VER1_ALLUSER = 3
    C_B4_VER1_NOUSER = 4
    C_DUR_VER1_ALLUSER = 5
    C_DUR_VER1_NOUSER = 6
    C_B4_SUB2_ALLUSER = 13
    C_DONE_ALLUSER = 14
    C_DONE_NOUSER = 15
    C_B4_REP1_ALLUSER = 7
    C_B4_REP1_NOUSER = 8
    C_B4_APPR1_ALLUSER = 9
    C_B4_APPR1_NOUSER = 10

    V_DUR_VER1_ALLUSER = 1
    V_DUR_VER1_NOUSER = 2
    V_B4_SUB2_ALLUSER = 9
    V_DONE_ALLUSER = 10
    V_DONE_NOUSER = 11
    V_B4_REP1_ALLUSER = 3
    V_B4_REP1_NOUSER = 4
    V_B4_APPR1_ALLUSER = 5
    V_B4_APPR1_NOUSER = 6

    # These notes are attached to various objects.
    # The ones with _AD were created by the admin, otherwise they were created by the author/curator/verifier used in the tests
    N_DUR_SUB1_ALLUSER = 1  # S_DUR_SUB1_ALLUSER
    N_DUR_SUB1_AUTHOR = 2  # S_DUR_SUB1_ALLUSER
    N_DUR_SUB1_AUTHOR_AD = 3  # S_DUR_SUB1_ALLUSER
    N_B4_ED1_ALLUSER = 7  # S_B4_ED1_ALLUSER
    N_B4_ED1_AUTHOR = 8  # S_B4_ED1_ALLUSER
    N_B4_ED1_AUTHOR_AD = 9  # S_B4_ED1_ALLUSER
    N_DUR_ED1_ALLUSER = 16  # E_DUR_ED1_ALLUSER
    N_DUR_ED1_EDITOR = 17  # E_DUR_ED1_ALLUSER
    N_DUR_ED1_EDITOR_AD = 18  # E_DUR_ED1_ALLUSER
    N_B4_CUR1_ALLUSER = 19  # E_B4_CUR1_ALLUSER
    N_B4_CUR1_EDITOR = 20  # E_B4_CUR1_ALLUSER
    N_B4_CUR1_EDITOR_AD = 21  # E_B4_CUR1_ALLUSER
    N_DUR_CUR1_ALLUSER = 22  # C_DUR_CUR1_ALLUSER
    N_DUR_CUR1_CURATOR = 23  # C_DUR_CUR1_ALLUSER
    N_DUR_CUR1_CURATOR_AD = 24  # C_DUR_CUR1_ALLUSER
    N_B4_VER1_ALLUSER = 25  # C_B4_VER1_ALLUSER
    N_B4_VER1_CURATOR = 26  # C_B4_VER1_ALLUSER
    N_B4_VER1_CURATOR_AD = 27  # C_B4_VER1_ALLUSER
    N_DUR_VER1_ALLUSER = 28  # V_DUR_VER1_ALLUSER
    N_DUR_VER1_VERIF = 29  # V_DUR_VER1_ALLUSER
    N_DUR_VER1_VERIF_AD = 30  # V_DUR_VER1_ALLUSER
    N_B4_SUB2_ALLUSER = 31  # V_B4_SUB2_ALLUSER
    N_B4_SUB2_VERIF = 32  # V_B4_SUB2_ALLUSER
    N_B4_SUB2_VERIF_AD = 33  # V_B4_SUB2_ALLUSER

    # Fixture is initialized here so we can call it once per class instead of method.
    # Downside is we could munge our test data. Seems worthwhile for now
    def setUpTestData():
        call_command("loaddata", "manuscript_submission_states.json", verbosity=0)


#####################################################################################################################################################
########## AUTHOR
#####################################################################################################################################################
class TestAuthorUrlAccess(BaseTestWithFixture):
    def test_AuthorAccess_IndexOther(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        # Authors can only view their own manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_NOUSER})).status_code, 404)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 404)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 404)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_AuthorAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)

        # Only editor/curator can progress manuscript
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)

        ### Author can never create/edit manuscript.
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)

        ### Author should always be able to read manuscript contents when assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Author cannot delete from manuscript. Note these tests call gitlab (which mocked) and don't error if a specific file is missing
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab

    def test_AuthorAccess_ManuscriptAssign(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        ### Author should always be able to invite other authors, but no other roles
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Only curators can unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_AuthorAccess_Submission(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        ### Author can create submissions when one isn't already created. Post will probably break once we have any fields on the submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        # This errors after we allowed notes to be added during create. Error: ['ManagementForm data is missing or has been tampered with'].
        # Only happens during this create (not ed/cur/ver), and only during these tests. Maybe something related to the empty post body and sub having no fields of its own???
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_NEW_ALLUSER      })).status_code, 404)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_ALLUSER  })).status_code, 200)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_AUTHOR   })).status_code, 200)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DUR_SUB1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_DONE_ALLUSER     })).status_code, 404)
        # self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.M_B4_SUB1_NOUSER   })).status_code, 404)

        ### All submission edit actions should only be doable when a submission is in progress
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)

        ### Read should be doable at any point there is a submission
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)

        # TODO: Why is this commented out?
        ### Author cannot create these
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_ED1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createverification", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)

        # We currently allow creating, editing, deleting notes they own at any point, even though the ui doesn't provide a path to the page when its not editing
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)

        ### Author can only delete from their own submission
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            302,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_ED1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F})).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)

        # cannot generate report or return the report
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_AuthorAccess_Edition(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)

        ### cannot edit editions in any way
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_NOUSER})).status_code, 404)

        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_AuthorAccess_Curation(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)

        ### Author cannot edit curations
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)

        ### For author, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_NOUSER})).status_code, 404)

        ### Author cannot edit curation notes
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_AuthorAccess_Verification(self, mock_gitlab_file_list):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        cl = Client()
        cl.force_login(author)

        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_NOUSER})).status_code, 404)

        ### Author cannot edit verifications
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### For author, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### Author cannot add notes to verifications
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)


# Ok so... curator needs fixing for sure
# Right now it can view all manuscripts, but the perm check in a lot of places only looks for "object based", not global (I think)
# Also right not curator can't do any assignments which... it absolutely needs to do.
# ...
# Maybe someday we'll need curators who can only see their assignments, but for now I should just design to not block that out

#####################################################################################################################################################
########## Curator
#####################################################################################################################################################
# NOTE: Curators have fairly verbose edit prividges, but they are not shown in the UI. There needs to be more discussions on what is needed.
class TestCuratorUrlAccess(BaseTestWithFixture):
    def test_CuratorAccess_IndexOther(self):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        # Curators can view all manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_NOUSER})).status_code, 200)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 200)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 200)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 200)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 200)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_CuratorAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 200)

        # Only curator/editor can progress manuscript, the ones they are assigned.
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH_ED})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Curator can only create/edit manuscripts they are assigned. Only after a round is completed.
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)

        ### Curator should always be able to read manuscript contents, even if not assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_NOUSER})).status_code, 200)

        ### Curator can delete from manuscript. Note these tests call gitlab (which mocked) and don't error if a specific file is missing
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            302,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_CUR1_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab

    def test_CuratorAccess_ManuscriptAssign(self):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        ### Curator can invite all roles
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Only curators can unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_ED1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_ED1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_ED1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_ED1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_CuratorAccess_Submission(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        ### Curator cannot create submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)

        ### Curator cannot edit submission
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)

        ### For curator, read should be doable at any point there is a submission completed
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 200)

        # Curator cannot add notes to submission
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)

        ### Curator cannot delete submission files
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_ED1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER})).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)

        # can generate report but not return it
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_CuratorAccess_Edition(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)

        ### cannot edit editions in any way
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_NOUSER})).status_code, 200)

        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_CuratorAccess_Curation(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)

        ### Curator can edit curations they are assigned at the right phase
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)

        ### For curator, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_NOUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_NOUSER})).status_code, 200)

        ### We currently allow creating, editing, deleting notes they own at any point, even though the ui doesn't provide a path to the page when its not editing
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER  })).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_SUB2_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_CuratorAccess_Verification(self, mock_gitlab_file_list):
        curator = m.User.objects.get(email="fakecurator@gmail.com")
        cl = Client()
        cl.force_login(curator)

        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_NOUSER})).status_code, 404)

        ### Curator cannot edit verifications
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### For curator, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_NOUSER})).status_code, 200)

        ### Curator cannot add notes to verifications
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)


#####################################################################################################################################################
########## Editor
#####################################################################################################################################################
class TestEditorUrlAccess(BaseTestWithFixture):
    def test_EditorAccess_IndexOther(self):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        # Editors can view assigned manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_NOUSER})).status_code, 404)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 404)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 404)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_EditorAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 200)

        # Only curator/editor can progress manuscript, the ones they are assigned.
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH_ED})).status_code, 302)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Editor can only create/edit manuscripts they are assigned
        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)

        ### Editors should always be able to read manuscript contents only when assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Editor can delete from manuscript. Note these tests call gitlab (which mocked) and don't error if a specific file is missing
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            302,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_CUR1_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab

    def test_EditorAccess_ManuscriptAssign(self):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        ### Editor can only invite author
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Only curators can unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_EditorAccess_Submission(self, mock_gitlab_file_list):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        ### Editor cannot create submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)

        ### Editor cannot edit submission
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)

        ### For editor, read should be doable at any point there is a submission completed, if they are assigned
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)

        # Editor cannot add notes to submission
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER , 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)

        ### Editor cannot delete submission files
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_ED1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER})).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)

        # Editor cannot generate report but can return the report
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_EditorAccess_Edition(self, mock_gitlab_file_list):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)

        ### Editor can edit editions they own
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_NOUSER})).status_code, 404)

        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER  })).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_SUB2_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 200)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 302)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_EditorAccess_Curation(self, mock_gitlab_file_list):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)

        ### Editor cannot edit curations in any way
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_NOUSER})).status_code, 404)

        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_EditorAccess_Verification(self, mock_gitlab_file_list):
        editor = m.User.objects.get(email="fakeeditor@gmail.com")
        cl = Client()
        cl.force_login(editor)

        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_NOUSER})).status_code, 404)

        ### Editor cannot edit verifications
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### For editor, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### Editor cannot add notes to verifications
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)


#####################################################################################################################################################
########## Verifier
#####################################################################################################################################################
class TestVerifierUrlAccess(BaseTestWithFixture):
    def test_EditorAccess_IndexOther(self):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        # Verifiers can view assigned manuscripts and submissions
        self.assertEqual(cl.get(reverse("index")).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_table")).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_table", kwargs={"manuscript_id": self.M_DONE_NOUSER})).status_code, 404)

        # pain to test # self.assertEqual(cl.get(reverse("account_associate_oauth")).status_code, 200)
        self.assertEqual(cl.get(reverse("account_user_details")).status_code, 200)
        self.assertEqual(cl.get(reverse("notifications")).status_code, 200)
        self.assertEqual(cl.get(reverse("site_actions")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteeditor")).status_code, 404)
        self.assertEqual(cl.get(reverse("invitecurator")).status_code, 404)
        self.assertEqual(cl.get(reverse("inviteverifier")).status_code, 404)
        self.assertEqual(cl.get(reverse("logout")).status_code, 302)

    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_VerifierAccess_ManuscriptCreateEdit(self, mock_gitlab_file_list):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        ###We only test binders we can't access, because it redirects to an external service (and the functionality is not flushed out)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_DONE_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("manuscript_binder", kwargs={'id':self.M_NEW_NOUSER   })).status_code, 200)

        # Verifier cannot create/edit/progress manuscripts
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH_ED})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_AUTH})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_progress", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("manuscript_create")).status_code, 403)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_edit", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_uploadfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_fileslist", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)

        ### Verifier should always be able to read manuscript contents when assigned
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_read", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("manuscript_readfiles", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Verifier cannot delete from manuscript. Note these tests call gitlab (which mocked) and don't error if a specific file is missing
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_CUR1_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("manuscript_deletefile", kwargs={"manuscript_id": self.M_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("manuscript_deletefile", kwargs={'manuscript_id':self.M_NEW_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab

    def test_VerifierAccess_ManuscriptAssign(self):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        ### Verifier cannot assign
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_inviteassignauthor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigneditor", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assigncurator", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_assignverifier", kwargs={"id": self.M_DONE_NOUSER})).status_code, 404)

        ### Verifier cannot unassign
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignauthor", kwargs={"user_id": 3, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 3, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigneditor", kwargs={"user_id": 4, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassigncurator", kwargs={"user_id": 5, "id": self.M_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_unassignverifier", kwargs={"user_id": 6, "id": self.M_DONE_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_VerifierAccess_Submission(self, mock_gitlab_file_list):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        ### Verifier cannot create submission.
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_NEW_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_AUTHOR})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("manuscript_createsubmission", kwargs={"manuscript_id": self.M_B4_SUB1_NOUSER})).status_code, 404)

        ### Verifier cannot edit submission
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_info", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_editfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_uploadfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_fileslist", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)

        ### For verifier, read should be doable at any point there is a submission completed if assigned
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_read", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_readfiles", kwargs={"id": self.S_DUR_VER1_NOUSER})).status_code, 404)

        # Verifier cannot add notes to submission
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_SUB1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_ED1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_createnote", kwargs={'submission_id':self.S_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("submission_editnote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_DUR_SUB1_ALLUSER, 'id':self.N_DUR_SUB1_AUTHOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("submission_deletenote", kwargs={'submission_id':self.S_B4_ED1_ALLUSER, 'id':self.N_B4_ED1_AUTHOR_AD})).status_code, 404)

        ### Verifier cannot delete submission files
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        self.assertEqual(
            cl.post(
                reverse("submission_deletefile", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER}) + "?file_path=hsis-merge-external-tool.json"
            ).status_code,
            404,
        )
        # can't test with mock #self.assertEqual(cl.post(reverse("submission_deletefile", kwargs={'submission_id':self.S_B4_ED1_ALLUSER })+"?file_path=hsis-merge-external-tool.json").status_code, 404) #there are no GitFiles actually on here, but delete just passes through to gitlab
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_ALLUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_DUR_SUB1_NOUSER_F})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_deleteallfiles", kwargs={"submission_id": self.S_B4_SUB2_ALLUSER})).status_code, 404)

        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_SUB1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_progress", kwargs={"id": self.S_DUR_VER1_ALLUSER})).status_code, 404)

        # cannot generate report or return the report
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_sendreport", kwargs={"id": self.S_B4_REP1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("submission_finish", kwargs={"id": self.S_B4_APPR1_NOUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_VerifierAccess_Edition(self, mock_gitlab_file_list):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createedition", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)

        ### cannot edit editions in any way
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_edit", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)

        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("edition_read", kwargs={"id": self.E_DUR_CUR1_NOUSER})).status_code, 404)

        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_ED1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_B4_CUR1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_createnote", kwargs={'edition_id':self.E_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("edition_editnote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_DUR_ED1_ALLUSER, 'id':self.N_DUR_ED1_EDITOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("edition_deletenote", kwargs={'edition_id':self.E_B4_CUR1_ALLUSER, 'id':self.N_B4_CUR1_EDITOR_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_ED1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("edition_progress", kwargs={"id": self.E_DUR_CUR1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_VerifierAccess_Curation(self, mock_gitlab_file_list):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createcuration", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 404)

        ### Verifier cannot edit curations
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_edit", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)

        ### For verifier, read should be doable at any point there is a curation completed and they are assigned
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DONE_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_B4_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("curation_read", kwargs={"id": self.C_DUR_VER1_NOUSER})).status_code, 404)

        ### Verifier cannot do notes on curations
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_SUB2_ALLUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_CUR1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_B4_VER1_NOUSER  })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_createnote", kwargs={'curation_id':self.C_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.get(reverse("curation_editnote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_DUR_CUR1_ALLUSER, 'id':self.N_DUR_CUR1_CURATOR_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_ALLUSER})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR})).status_code, 404)
        # self.assertEqual(cl.post(reverse("curation_deletenote", kwargs={'curation_id':self.C_B4_VER1_ALLUSER, 'id':self.N_B4_VER1_CURATOR_AD})).status_code, 404)

        # TODO: This shouldn't work, verifier should not be able to progress a curation
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_CUR1_NOUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("curation_progress", kwargs={"id": self.C_DUR_VER1_ALLUSER})).status_code, 404)

    @mock.patch("corere.main.views.classes.helper_populate_gitlab_files_submission", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_delete_file", mock.Mock())
    @mock.patch("corere.main.views.main.gitlab_submission_delete_all_files", mock.Mock())
    @mock.patch("corere.main.views.classes.gitlab_repo_get_file_folder_list", return_value=[])
    def test_VerifierAccess_Verification(self, mock_gitlab_file_list):
        verifier = m.User.objects.get(email="fakeverifier@gmail.com")
        cl = Client()
        cl.force_login(verifier)

        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_ED1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("submission_createverification", kwargs={"submission_id": self.S_B4_VER1_NOUSER})).status_code, 404)

        ### Verifier can edit verifications on assigned manuscripts
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 404)
        self.assertEqual(cl.get(reverse("verification_edit", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        ### For verifiers, read should be doable at any point there is a curation completed
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_B4_SUB2_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_ALLUSER})).status_code, 200)
        self.assertEqual(cl.get(reverse("verification_read", kwargs={"id": self.V_DONE_NOUSER})).status_code, 404)

        # Verifiers can edit notes on curations when assigned
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER })).status_code, 200)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_ALLUSER    })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DONE_NOUSER     })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_createnote", kwargs={'verification_id':self.V_DUR_VER1_NOUSER })).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 200)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 200)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 200)
        # self.assertEqual(cl.get(reverse("verification_editnote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF})).status_code, 302)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_DUR_VER1_ALLUSER, 'id':self.N_DUR_VER1_VERIF_AD})).status_code, 404)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_ALLUSER})).status_code, 302)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF})).status_code, 302)
        # self.assertEqual(cl.post(reverse("verification_deletenote", kwargs={'verification_id':self.V_B4_SUB2_ALLUSER, 'id':self.N_B4_SUB2_VERIF_AD})).status_code, 404)

        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 302)
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_ALLUSER})).status_code, 404)  # can't call twice
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.V_DUR_VER1_NOUSER})).status_code, 404)
        # TODO: I thought the below code would let me call it (because its buggy), but I wasn't able to. I guess my curation/verification overlap isn't quite clearcut
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)
        self.assertEqual(cl.post(reverse("verification_progress", kwargs={"id": self.C_DUR_CUR1_ALLUSER})).status_code, 404)  # can't call twice
