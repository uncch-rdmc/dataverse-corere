import json, unittest, mock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from corere.main.middleware import local
from corere.main import constants as c
from corere.main import models as m
from django.contrib.auth.models import Permission, Group
from rest_framework import status
from http import HTTPStatus

class TestUrls(TestCase):
    
    #TODO: Test associate/logout/etc urls
    #TODO: How to test deletefiles good?

    @mock.patch('corere.main.models.gitlab_create_manuscript_repo', mock.Mock())
    @mock.patch('corere.main.models.gitlab_create_submissions_repo', mock.Mock())
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('temporary', 'temporary@gmail.com', 'temporary')
        self.user2 = User.objects.create_user('temporary2', 'temporary2@gmail.com', 'temporary2')
        Group.objects.get(name=c.GROUP_ROLE_EDITOR).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_ROLE_VERIFIER).user_set.add(self.user2)
        local.user = self.user2 #needed for middleware that saves creator/updater. Note that this does play into perms.
        #Create needed objects. Maybe should be a fixture.
        self.manuscript = m.Manuscript()
        self.manuscript._status = m.MANUSCRIPT_AWAITING_INITIAL
        self.manuscript.save()

        local.user = None
        # self.submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        # self.submission.save()
        # self.curation = m.Curation()
        # self.curation.submission = submission
        # self.curation.save()
        # self.verification = m.Verification()
        # self.verification.submission = submission
        # self.submission._status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        # self.submission.save()
        # self.verification.save()

    # @unittest.skip("Don't want to test")
    def test_manuscript_urls_not_logged_in(self):
        #Add user 2 to roles on manuscript, to test removal correctly
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        resp = self.client.get(reverse("manuscript_create"))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        ## Not implemented yet
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        # self.assertEqual(resp.status_code, 302)
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        # self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_table"))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)      
        resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)  

    # @unittest.skip("Don't want to test")
    def test_manuscript_urls_logged_in_no_role(self):
        #Add user 2 to roles on manuscript, to test removal
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        
        User = get_user_model()
        self.client.login(username='temporary', password='temporary')
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        resp = self.client.get(reverse("manuscript_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        ## Not implemented yet
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        # self.assertEqual(resp.status_code, 404)
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        # self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_table"))
        self.assertEqual(resp.status_code, 200) #returns but should be blank (untested here)
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)    
        resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

    #multiple roles at once makes it a bit easier to test access, tho its possible it'd overlook a role based access bug.
    # @unittest.skip("Don't want to test")
    @mock.patch('corere.main.models.gitlab_create_submissions_repo', mock.Mock())
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_manuscript_urls_logged_in_multiple_roles(self, mock_gitlab_file_list):
        local.user = self.user #Not sure if nessecary 
        #Certain access is needed to actually test pages
        Group.objects.get(name=c.GROUP_ROLE_EDITOR).user_set.add(self.user) #test user is editor
        Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is editor on manuscript 1
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.user) #test user is curator
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is curator on manuscript 1
        Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(self.user) #test user is authorr
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is author on manuscript 1
        #Add user 2 to roles on manuscript, to test removal correctly... well except for its commented out
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        User = get_user_model()
        self.client.login(username='temporary', password='temporary')
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        #print(self.user.groups.all())
        resp = self.client.get(reverse("manuscript_create"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_edit", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_editfiles", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_read", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_addauthor", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_addcurator", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_addverifier", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        ## Not implemented yet
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        # self.assertEqual(resp.status_code, 404)
        # resp = self.client.get(reverse("manuscript_deleteauthor", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        # self.assertEqual(resp.status_code, 404)
        ## Untested because effort to set up
        # resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        # self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_deletecurator", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        ## Untested because effort to set up
        # resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id, 'user_id': self.user2.id}))
        # self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_deleteverifier", kwargs={'id':self.manuscript.id+1, 'user_id': self.user2.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("manuscript_createsubmission", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("manuscript_table"))
        self.assertEqual(resp.status_code, 200) 
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_table", kwargs={'manuscript_id':self.manuscript.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        #Manuscript is not in a state to be progressed so it returns 404
        # resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id}))
        # self.assertEqual(resp.status_code, 200)
        # resp = self.client.get(reverse("manuscript_progress", kwargs={'id':self.manuscript.id+1})) #id we know hasn't been created
        # self.assertEqual(resp.status_code, 404)

    # @unittest.skip("Don't want to test")
    def test_submission_curation_verification_urls_not_logged_in(self):
        #Add user2 to roles on manuscript, to test removal
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        ######### SUBMISSION (create in cur/ver) #########
        
        submission = m.Submission()
        submission.manuscript = self.manuscript
        submission.save()

        #Add user2 to roles on manuscript, to test removal correctly
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        
        # User = get_user_model()
        # self.client.login(username='temporary', password='temporary')
        # resp = self.client.get(url)
        # self.assertEqual(resp.status_code, 302)

        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        local.user = None #accessing pages sets local.user=AnonymousUser which blows up our save tracking (anon users will never be creating in real runs)
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        self.manuscript._status = m.MANUSCRIPT_PROCESSING
        self.manuscript.save()
        sub_note = m.Note()
        sub_note.parent_submission = submission
        sub_note.save()
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        
        ######### CURATION (besides create) #########

        local.user = None #accessing pages sets local.user=AnonymousUser which blows up our save tracking (anon users will never be creating in real runs)
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        curation = m.Curation()
        curation.submission = submission
        curation.save()

        cur_note = m.Note()
        cur_note.parent_curation = curation
        cur_note.save()

        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)

        ######### VERIFICATION (besides create) #########

        local.user = None #accessing pages sets local.user=AnonymousUser which blows up our save tracking (anon users will never be creating in real runs)
        curation._status = m.CURATION_NO_ISSUES
        curation.save()
        submission._status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        submission.save()

        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)

        local.user = None #accessing pages sets local.user=AnonymousUser which blows up our save tracking (anon users will never be creating in real runs)
        verification = m.Verification()
        verification.submission = submission
        verification.save()
        ver_note = m.Note()
        ver_note.parent_verification = verification
        ver_note.save()

        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 302)
 
    # @unittest.skip("Don't want to test")
    def test_submission_curation_verification_urls_logged_in_no_role(self):
        #Add user2 to roles on manuscript, to test removal
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        
        User = get_user_model()
        self.client.login(username='temporary', password='temporary')
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        ######### SUBMISSION (create in cur/ver) #########

        local.user = None
        submission = m.Submission()
        submission.manuscript = self.manuscript
        submission.save()

        #Add user2 to roles on manuscript, to test removal correctly
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        
        # User = get_user_model()
        # self.client.login(username='temporary', password='temporary')
        # resp = self.client.get(url)
        # self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        self.manuscript._status = m.MANUSCRIPT_PROCESSING
        self.manuscript.save()
        sub_note = m.Note()
        sub_note.parent_submission = submission
        sub_note.save()
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        
        ######### CURATION (besides create) #########

        local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        curation = m.Curation()
        curation.submission = submission
        curation.save()

        cur_note = m.Note()
        cur_note.parent_curation = curation
        cur_note.save()

        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        ######### VERIFICATION (besides create) #########

        local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        curation._status = m.CURATION_NO_ISSUES
        curation.save()
        submission._status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        submission.save()

        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        verification = m.Verification()
        verification.submission = submission
        verification.save()
        ver_note = m.Note()
        ver_note.parent_verification = verification
        ver_note.save()

        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

    #all roles at once makes it a bit easier to test access, tho its possible it'd overlook a role based access bug.
    @mock.patch('corere.main.views.classes.gitlab_repo_get_file_folder_list', return_value=[])
    def test_submission_curation_verification_urls_logged_in_all_roles(self, mock_gitlab_file_list):
        local.user = self.user #Not sure if nessecary 
        #Certain access is needed to actually test pages
        Group.objects.get(name=c.GROUP_ROLE_EDITOR).user_set.add(self.user) #test user is editor
        Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is editor on manuscript 1
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.user) #test user is curator
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is curator on manuscript 1
        Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(self.user) #test user is author
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is author on manuscript 1
        Group.objects.get(name=c.GROUP_ROLE_VERIFIER).user_set.add(self.user) #test user is author
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user) #test user is author on manuscript 1
        #Add user2 to roles on manuscript, to test removal correctly... well except for its commented out
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)

        User = get_user_model() #MAD: DELETE THIS? IN MULTIPLE PLACES?
        self.client.login(username='temporary', password='temporary')
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)


        ######### SUBMISSION (create in cur/ver) #########

        local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        submission = m.Submission()
        submission.manuscript = self.manuscript
        submission.save()

        #Add user2 to roles on manuscript, to test removal correctly
        #Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.user2)
        
        # User = get_user_model()
        # self.client.login(username='temporary', password='temporary')
        # resp = self.client.get(url)
        # self.assertEqual(resp.status_code, 200)

        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_edit", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_read", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_editfiles", kwargs={'id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        #For this test we make the local user actually the note "author" so we can test edit/delete
        #local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        self.manuscript._status = m.MANUSCRIPT_PROCESSING
        self.manuscript.save()
        sub_note = m.Note()
        sub_note.parent_submission = submission
        sub_note.save()
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_createcuration", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_createnote", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_editnote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id}))
        self.assertEqual(resp.status_code, 302) #redirects after success
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id, 'id':sub_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("submission_deletenote", kwargs={'submission_id':submission.id+1, 'id':sub_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        
        ######### CURATION (besides create) #########

        #For this test we make the local user actually the note "author" so we can test edit/delete
        #local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        curation = m.Curation()
        curation.submission = submission
        curation.save()

        cur_note = m.Note()
        cur_note.parent_curation = curation
        cur_note.save()

        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("curation_edit", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("curation_read", kwargs={'id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("curation_createnote", kwargs={'curation_id':curation.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_editnote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id}))
        self.assertEqual(resp.status_code, 302) #redirects after success
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id, 'id':cur_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("curation_deletenote", kwargs={'curation_id':curation.id+1, 'id':cur_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        ######### VERIFICATION (besides create) #########

        #For this test we make the local user actually the note "author" so we can test edit/delete
        #local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        curation._status = m.CURATION_NO_ISSUES
        curation.save()
        submission._status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        submission.save()

        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("submission_createverification", kwargs={'submission_id':submission.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        #For this test we make the local user actually the note "author" so we can test edit/delete
        #local.user = None #used to set perms on note creation, we don't want an owner. Has to be right before to ensure local.user is None
        verification = m.Verification()
        verification.submission = submission
        verification.save()
        ver_note = m.Note()
        ver_note.parent_verification = verification
        ver_note.save()

        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("verification_edit", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("verification_read", kwargs={'id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("verification_createnote", kwargs={'verification_id':verification.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_editnote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id}))
        self.assertEqual(resp.status_code, 302) #redirects after success
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id, 'id':ver_note.id+1})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("verification_deletenote", kwargs={'verification_id':verification.id+1, 'id':ver_note.id})) #id we know hasn't been created
        self.assertEqual(resp.status_code, 404)