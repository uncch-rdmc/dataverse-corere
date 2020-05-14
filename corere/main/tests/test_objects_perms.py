import json, unittest, mock
from django.test import TestCase
from corere.main.middleware import local
from django.db.utils import IntegrityError
from django.db import transaction
from corere.main import models as m
from corere.main import constants as c
from django.core.exceptions import FieldError
from django.contrib.auth.models import Permission, Group
from django_fsm import has_transition_perm, TransitionNotAllowed

#TODO: Encapsulating all the previous TODOs:
# - Test manuscript/file notes in test_create_manuscript_objects when available
# - Add extra notes test that covers more edge-cases
# - Test that other users can't do the various transitions. Include canview canedit. Maybe in test_basic_manuscript_cycle_and_fsm_permissions_direct
# - Maybe add a test related to the nested submission.submit/manuscript.process perms
# - Add Integration tests! Make sure each role can only do the things we want!
# - Still running into issues calling specific tests, this notation won't work ./manage.py test corere.main.tests.TestModels.test_create_manuscript_objects
# - With further testing we'll also need more mocks. Currently all our mocking does is "do nothing". 
#    More advanced mocks seem to require passing the mocks as args to the functions, even if they aren't used in there? 
#    Some useful resources when getting back into that:
#       - https://docs.python.org/3/library/unittest.mock.html#where-to-patch
#       - https://fgimian.github.io/blog/2014/04/10/using-the-python-mock-library-to-fake-regular-functions-during-tests/
#       - https://stackoverflow.com/questions/15352315/django-mock-patch-doesnt-work-as-i-expect

#@unittest.skip("Don't want to test")
class TestModels(TestCase):
    def setUp(self):
        self.user = m.User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        local.user = self.user #needed for middleware that saves creator/updater

    #This tests ensures that manuscripts/submissions/curations/verifications/notes can be created.
    #Furthermore, it tests the restrictions related to creating and connecting these objects.

    @mock.patch('corere.main.models.gitlab_create_manuscript_repo', mock.Mock())
    def test_create_manuscript_objects(self):
        manuscript = m.Manuscript()
        manuscript.save()
        m2 = m.Manuscript.objects.get(id=manuscript.id)
        self.assertEqual(manuscript, m2)

        #-------------------------------------------------

        submission = m.Submission()
        with self.assertRaises(IntegrityError) as exc_sub1, transaction.atomic(): #cannot save without manuscript
            submission.save()
        self.assertTrue('null value in column "manuscript_id" violates not-null constraint' in str(exc_sub1.exception))

        submission.manuscript = manuscript
        with self.assertRaises(FieldError) as exc_sub2, transaction.atomic():
            submission.save()
        self.assertTrue('A submission cannot be created unless a manuscript status is set to await it' in str(exc_sub2.exception))
        manuscript._status = m.MANUSCRIPT_AWAITING_INITIAL
        submission.save()

        sub_t = m.Submission.objects.get(id=submission.id)
        self.assertEqual(submission, sub_t)
        sub_note = m.Note()
        sub_note.parent_submission = submission
        sub_note.save()
        sub_note_t = m.Note.objects.get(id=sub_note.id)
        self.assertEqual(sub_note, sub_note_t)

        with self.assertRaises(FieldError) as exc_sub3, transaction.atomic():
            submission2bad = m.Submission()
            submission2bad.manuscript = manuscript
            submission2bad.save()
        self.assertTrue('A submission is already in progress for this manuscript' in str(exc_sub3.exception))

        #-------------------------------------------------

        curation = m.Curation()
        with self.assertRaises(IntegrityError) as exc_cur1, transaction.atomic(): #cannot save without submission
            curation.save()
        self.assertTrue('null value in column "submission_id" violates not-null constraint' in str(exc_cur1.exception))
        
        curation.submission = submission
        with self.assertRaises(FieldError) as exc_cur2, transaction.atomic(): #cannot save without submission
            curation.save()
        self.assertTrue('A curation cannot be added to a submission unless its status is: in_progress_curation' in str(exc_cur2.exception))

        submission._status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        curation.save()
        cur_t = m.Curation.objects.get(id=curation.id)
        self.assertEqual(curation, cur_t)
        cur_note = m.Note()
        cur_note.parent_curation = curation
        cur_note.save()
        cur_note_t = m.Note.objects.get(id=cur_note.id)
        self.assertEqual(cur_note, cur_note_t)

        with self.assertRaises(IntegrityError) as exc_cur3, transaction.atomic():
            curation2bad = m.Curation()
            curation2bad.submission = submission
            curation2bad.save()
        self.assertTrue('duplicate key value violates unique constraint "main_curation_submission_id_key"' in str(exc_cur3.exception))

        #-------------------------------------------------

        verification = m.Verification()
        with self.assertRaises(IntegrityError) as exc_ver1, transaction.atomic(): #cannot save without submission
            verification.save()
        self.assertTrue('null value in column "submission_id" violates not-null constraint' in str(exc_ver1.exception))
        
        verification.submission = submission
        with self.assertRaises(FieldError) as exc_ver2, transaction.atomic(): #cannot save without submission
            verification.save()
        self.assertTrue('A verification cannot be added to a submission unless its status is: in_progress_verification' in str(exc_ver2.exception))
        
        submission._status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        submission.save()
        verification.save()
        ver_t = m.Verification.objects.get(id=verification.id)
        self.assertEqual(verification, ver_t)
        ver_note = m.Note()
        ver_note.parent_verification = verification
        ver_note.save()
        ver_note_t = m.Note.objects.get(id=ver_note.id)
        self.assertEqual(ver_note, ver_note_t)

        with self.assertRaises(IntegrityError) as exc_ver3, transaction.atomic():
            verification2bad = m.Verification()
            verification2bad.submission = submission
            verification2bad.save()
        self.assertTrue('duplicate key value violates unique constraint "main_verification_submission_id_key"' in str(exc_ver3.exception))

class TestManuscriptWorkflow(TestCase):
    def setUp(self):
        self.editor = m.User.objects.create_user('editor') #gotta have a user to create a manuscript
        self.author = m.User.objects.create_user('author')
        self.curator = m.User.objects.create_user('curator')
        self.verifier = m.User.objects.create_user('verifier')
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.editor)
        Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(self.author)
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.curator)
        Group.objects.get(name=c.GROUP_ROLE_VERIFIER).user_set.add(self.verifier)
        #self.all_users = [self.editor,self.author,self.curator,self.verifier]
        local.user = self.editor #has to be set to something for saving (middleware uses it to set creator/updater).

    #@unittest.skip("Don't want to test")
    @mock.patch('corere.main.models.gitlab_create_manuscript_repo', mock.Mock())
    def test_basic_manuscript_cycle_and_fsm_permissions_direct(self):

        #-------------- Create manuscript ----------------
        manuscript = m.Manuscript()
        manuscript.save()
        #TODO: Ideally we should be doing this via normal code paths. At least we should test the add author/curator/verifier flows
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id)).user_set.add(self.editor)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id)).user_set.add(self.curator)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(manuscript.id)).user_set.add(self.verifier)
        self.assertFalse(has_transition_perm(manuscript.begin, self.editor))        
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(manuscript.id)).user_set.add(self.author)
        self.assertTrue(has_transition_perm(manuscript.begin, self.editor))
        manuscript.begin()
        manuscript.save()
        self.assertFalse(has_transition_perm(manuscript.begin, self.editor)) #Shouldn't be able to begin after begun

        #################### ROUND 1 #####################
        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.process, self.author))
        submission = m.Submission()
        submission.manuscript = manuscript
        submission.save()
        self.assertTrue(has_transition_perm(manuscript.process, self.author))  
        self.assertTrue(has_transition_perm(submission.submit, self.author))   
        submission.submit(self.author)
        submission.save()
        self.assertFalse(has_transition_perm(manuscript.process, self.author))  
        self.assertFalse(has_transition_perm(submission.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed):
            submission.submit(self.author)

        #-------------- Create curation (pass) -----------
        self.assertEqual(submission._status, m.SUBMISSION_IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission.add_curation_noop, self.curator))
        curation = m.Curation()
        curation.submission = submission
        curation.save()
        self.assertTrue(has_transition_perm(curation.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission.review, self.curator))
        curation._status = m.CURATION_NO_ISSUES
        curation.save()
        self.assertTrue(has_transition_perm(submission.review, self.curator))
        submission.review()
        submission.save()
        self.assertEqual(submission._status, m.SUBMISSION_IN_PROGRESS_VERIFICATION)
        #TODO: This doesn't fail because you call review again for verification
        #      If we break up review we should check again... 
        # with self.assertRaises(TransitionNotAllowed):
        #     submission.review()

        #--------- Create verification (fail) ------------
        self.assertEqual(submission._status, m.SUBMISSION_IN_PROGRESS_VERIFICATION)
        self.assertTrue(has_transition_perm(submission.add_verification_noop, self.verifier))
        verification = m.Verification()
        verification.submission = submission
        verification.save()
        self.assertTrue(has_transition_perm(verification.edit_noop, self.verifier))
        self.assertFalse(has_transition_perm(submission.review, self.verifier))
        verification._status = m.VERIFICATION_MINOR_ISSUES
        verification.save()
        self.assertTrue(has_transition_perm(submission.review, self.verifier))
        submission.review()
        submission.save()
        self.assertEqual(submission._status, m.SUBMISSION_REVIEWED)
        self.assertEqual(manuscript._status, m.MANUSCRIPT_AWAITING_RESUBMISSION)
        with self.assertRaises(TransitionNotAllowed):
            submission.review()

        #################### ROUND 2 #####################

        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.process, self.author))
        submission2 = m.Submission()
        submission2.manuscript = manuscript
        submission2.save()
        self.assertTrue(has_transition_perm(manuscript.process, self.author))  
        self.assertTrue(has_transition_perm(submission2.submit, self.author))   
        submission2.submit(self.author)
        submission2.save()
        self.assertFalse(has_transition_perm(manuscript.process, self.author))  
        self.assertFalse(has_transition_perm(submission2.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed):
            submission2.submit(self.author)
        self.assertEqual(manuscript._status, m.MANUSCRIPT_PROCESSING)

        #-------------- Create curation (fail) -----------
        self.assertEqual(submission2._status, m.SUBMISSION_IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission2.add_curation_noop, self.curator))
        curation2 = m.Curation()
        curation2.submission = submission2
        curation2.save()
        self.assertTrue(has_transition_perm(curation2.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission2.review, self.curator))
        curation2._status = m.CURATION_MINOR_ISSUES
        curation2.save()
        self.assertTrue(has_transition_perm(submission2.review, self.curator))
        submission2.review()
        submission2.save()
        self.assertEqual(submission2._status, m.SUBMISSION_REVIEWED)
        self.assertEqual(manuscript._status, m.MANUSCRIPT_AWAITING_RESUBMISSION)

        #################### ROUND 3 #####################

        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.process, self.author))
        submission3 = m.Submission()
        submission3.manuscript = manuscript
        submission3.save()
        self.assertTrue(has_transition_perm(manuscript.process, self.author))  
        self.assertTrue(has_transition_perm(submission3.submit, self.author))   
        submission3.submit(self.author)
        submission3.save()
        self.assertFalse(has_transition_perm(manuscript.process, self.author))  
        self.assertFalse(has_transition_perm(submission3.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed):
            submission3.submit(self.author)

        #-------------- Create curation (pass) -----------
        self.assertEqual(submission3._status, m.SUBMISSION_IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission3.add_curation_noop, self.curator))
        curation3 = m.Curation()
        curation3.submission = submission3
        curation3.save()
        self.assertTrue(has_transition_perm(curation3.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission3.review, self.curator))
        curation3._status = m.CURATION_NO_ISSUES
        curation3.save()
        self.assertTrue(has_transition_perm(submission3.review, self.curator))
        submission3.review()
        submission3.save()
        self.assertEqual(submission3._status, m.SUBMISSION_IN_PROGRESS_VERIFICATION)

        #--------- Create verification (pass) ------------
        self.assertEqual(submission3._status, m.SUBMISSION_IN_PROGRESS_VERIFICATION)
        self.assertTrue(has_transition_perm(submission3.add_verification_noop, self.verifier))
        verification3 = m.Verification()
        verification3.submission = submission3
        verification3.save()
        self.assertTrue(has_transition_perm(verification3.edit_noop, self.verifier))
        self.assertFalse(has_transition_perm(submission3.review, self.verifier))
        verification3._status = m.VERIFICATION_SUCCESS
        verification3.save()
        self.assertTrue(has_transition_perm(submission3.review, self.verifier))
        submission3.review()
        submission3.save()
        self.assertEqual(submission3._status, m.SUBMISSION_REVIEWED)
        self.assertEqual(manuscript._status, m.MANUSCRIPT_COMPLETED)

### Test Helpers ###

#TODO: This is non-functional until we get integration tests set up
def get_url_success_users(url, r_type, users):
    success_users = []
    for u in users:
        #TOOD: change based upon get/post
        result = self.client.get(url)
        if(result.status_code == 200):
            success_users.append(u)
    return success_users