import json, unittest, mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from corere.main.middleware import local
from corere.main import constants as c
from corere.main import models as m
from django.contrib.auth.models import Permission, Group
from rest_framework import status
from http import HTTPStatus

@unittest.skip("Incomplete")
class TestUrlsFixture(TestCase):
    fixtures = ['manuscript_submission_states']

    def testFixtureLoad(self):
        manuscript = m.Manuscript.objects.get(pk=1)
        self.assertEquals(manuscript.doi, 'test')

    #Ok... so have these 10 manuscripts all set up, how do I want to break down these tests?
    # - Each test by user, and go through all the manuscripts?
    # - Each test by manuscript, and go through the users?


    def testAssignedAuthorAccessManuscript(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        c = Client()
        c.force_login(author)
        
        resp = c.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("manuscript_table"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_table", kwargs={'manuscript_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("manuscript_create"))
        self.assertEqual(resp.status_code, 403)
        resp = c.get(reverse("manuscript_edit", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_uploadfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_fileslist", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_read", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_readfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_inviteassignauthor", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_unassignauthor", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_assigneditor", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_unassigneditor", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_assigncurator", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_unassigncurator", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_assignverifier", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_unassignverifier", kwargs={'id':5, 'user_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_deletefile", kwargs={'manuscript_id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_binder", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)
        resp = c.get(reverse("manuscript_progress", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 404)

    def testAssignedAuthorAccessSubCurVer(self):
        author = m.User.objects.get(email="fakeauthor@gmail.com")
        c = Client()
        c.force_login(author)

        resp = c.get(reverse("submission_edit", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_editfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_uploadfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_fileslist", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_read", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_readfiles", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_createcuration", kwargs={'submission_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_createverification", kwargs={'submission_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_createnote", kwargs={'submission_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_editnote", kwargs={'submission_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_deletenote", kwargs={'submission_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_deletefile", kwargs={'submission_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_deleteallfiles", kwargs={'submission_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("submission_progress", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)

        resp = c.get(reverse("curation_edit", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("curation_read", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("curation_createnote", kwargs={'curation_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("curation_editnote", kwargs={'curation_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("curation_deletenote", kwargs={'curation_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("curation_progress", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        
        resp = c.get(reverse("verification_edit", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("verification_read", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("verification_createnote", kwargs={'verification_id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("verification_editnote", kwargs={'verification_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("verification_deletenote", kwargs={'verification_id':5, 'id':5}))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("verification_progress", kwargs={'id':5}))
        self.assertEqual(resp.status_code, 200)
        
    def testAssignedAuthorAccessOther(self):
        # untested currently
        # resp = c.get(reverse("account_associate_oauth", kwargs={'key':5}))
        # self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("account_user_details"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("notifications"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("site_actions"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("site_actions/inviteeditor"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("site_actions/invitecurator"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("site_actions/inviteverifier"))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse("logout"))
        self.assertEqual(resp.status_code, 200)