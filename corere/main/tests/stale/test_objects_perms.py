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

#@unittest.skip("Don't want to test")
class TestModels(TestCase):
    def setUp(self):
        self.user = m.User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        local.user = self.user #needed for middleware that saves creator/updater

    #This tests ensures that manuscripts/submissions/curations/verifications/notes can be created.
    #Furthermore, it tests the restrictions related to creating and connecting these objects.
    @mock.patch('corere.main.models.gitlab_create_manuscript_repo', mock.Mock())
    @mock.patch('corere.main.models.gitlab_create_submissions_repo', mock.Mock())
    @mock.patch('corere.main.models.gitlab_create_submission_branch', mock.Mock())
    def test_create_manuscript_objects(self):
        manuscript = m.Manuscript()
        manuscript.save()
        m2 = m.Manuscript.objects.get(id=manuscript.id)
        self.assertEqual(manuscript, m2)

        #-------------------------------------------------

        submission = m.Submission()
        with self.assertRaises(m.Manuscript.DoesNotExist) as exc_sub1, transaction.atomic(): #cannot save without manuscript
            submission.save()
        #self.assertTrue('null value in column "manuscript_id" violates not-null constraint' in str(exc_sub1.exception))

        submission.manuscript = manuscript
        with self.assertRaises(FieldError) as exc_sub2, transaction.atomic():
            submission.save()
        self.assertTrue('A submission cannot be created unless a manuscript status is set to await it' in str(exc_sub2.exception))
        manuscript._status = m.Manuscript.Status.AWAITING_INITIAL
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

        submission._status = m.Submission.Status.IN_PROGRESS_CURATION
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
        
        submission._status = m.Submission.Status.IN_PROGRESS_VERIFICATION
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
    @mock.patch('corere.main.models.gitlab_create_submissions_repo', mock.Mock())
    @mock.patch('corere.main.models.gitlab_create_submission_branch', mock.Mock())
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
        self.assertFalse(has_transition_perm(manuscript.review, self.author))
        submission = m.Submission()
        submission.manuscript = manuscript
        submission.save()
        self.assertTrue(has_transition_perm(manuscript.review, self.author))  
        self.assertTrue(has_transition_perm(submission.submit, self.author))   
        submission.submit(self.author)
        submission.save()
        self.assertFalse(has_transition_perm(manuscript.review, self.author))  
        self.assertFalse(has_transition_perm(submission.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed): #can't submit twice
            submission.submit(self.author)

        #-------------- Create editor review (fail) -----------
        self.assertEqual(submission._status, m.Submission.Status.IN_PROGRESS_EDITION)
        self.assertTrue(has_transition_perm(submission.add_edition_noop, self.editor))
        edition = m.Edition()
        edition.submission = submission
        edition.save()
        self.assertTrue(has_transition_perm(edition.edit_noop, self.editor))
        self.assertFalse(has_transition_perm(submission.submit_edition, self.editor))
        edition._status = m.Edition.Status.ISSUES
        edition.save()
        self.assertTrue(has_transition_perm(submission.submit_edition, self.editor))
        submission.submit_edition()
        submission.save()
        self.assertEqual(submission._status, m.Submission.Status.RETURNED)
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        #################### ROUND 2 #####################

        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.review, self.author))
        submission2 = m.Submission()
        submission2.manuscript = manuscript
        submission2.save()
        self.assertTrue(has_transition_perm(manuscript.review, self.author))  
        self.assertTrue(has_transition_perm(submission2.submit, self.author))   
        submission2.submit(self.author)
        submission2.save()
        self.assertFalse(has_transition_perm(manuscript.review, self.author))  
        self.assertFalse(has_transition_perm(submission2.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed): #can't submit twice
            submission2.submit(self.author)

        #-------------- Create editor review (pass) -----------
        self.assertEqual(submission2._status, m.Submission.Status.IN_PROGRESS_EDITION)
        self.assertTrue(has_transition_perm(submission2.add_edition_noop, self.editor))
        edition2 = m.Edition()
        edition2.submission = submission2
        edition2.save()
        self.assertTrue(has_transition_perm(edition2.edit_noop, self.editor))
        self.assertFalse(has_transition_perm(submission2.submit_edition, self.editor))
        edition2._status = m.Edition.Status.NO_ISSUES
        edition2.save()
        self.assertTrue(has_transition_perm(submission2.submit_edition, self.editor))
        submission2.submit_edition()
        submission2.save()
        self.assertEqual(submission2._status, m.Submission.Status.IN_PROGRESS_CURATION)

        #-------------- Create curation (pass) -----------
        self.assertEqual(submission2._status, m.Submission.Status.IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission2.add_curation_noop, self.curator))
        curation2 = m.Curation()
        curation2.submission = submission2
        curation2.save()
        self.assertTrue(has_transition_perm(curation2.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission2.review_curation, self.curator))
        curation2._status = m.Curation.Status.NO_ISSUES
        curation2.save()
        self.assertTrue(has_transition_perm(submission2.review_curation, self.curator))
        submission2.review_curation()
        submission2.save()
        self.assertEqual(submission2._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)
        #TODO: This doesn't fail because you call review again for verification
        #      If we break up review we should check again... 
        # with self.assertRaises(TransitionNotAllowed):
        #     submission2.review()

        #--------- Create verification (fail) ------------
        self.assertEqual(submission2._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)
        self.assertTrue(has_transition_perm(submission2.add_verification_noop, self.verifier))
        verification2 = m.Verification()
        verification2.submission = submission2
        verification2.save()
        self.assertTrue(has_transition_perm(verification2.edit_noop, self.verifier))
        self.assertFalse(has_transition_perm(submission2.review_verification, self.verifier))
        verification2._status = m.Verification.Status.MINOR_ISSUES
        verification2.save()
        self.assertTrue(has_transition_perm(submission2.review_verification, self.verifier))
        submission2.review_verification()
        submission2.save()
        self.assertEqual(submission2._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)
        with self.assertRaises(TransitionNotAllowed): #can't submit twice
            submission2.review_verification()

        #-------------- Create curator report -----------
        self.assertTrue(has_transition_perm(submission2.send_report, self.curator))
        submission2.send_report()
        submission2.save()
        self.assertEqual(submission2._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        #-------------- Create editor return -----------
        self.assertTrue(has_transition_perm(submission2.finish_submission, self.editor))
        submission2.finish_submission()
        submission2.save()
        self.assertEqual(submission2._status, m.Submission.Status.RETURNED)
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        #################### ROUND 3 #####################

        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.review, self.author))
        submission3 = m.Submission()
        submission3.manuscript = manuscript
        submission3.save()
        self.assertTrue(has_transition_perm(manuscript.review, self.author))  
        self.assertTrue(has_transition_perm(submission3.submit, self.author))   
        submission3.submit(self.author)
        submission3.save()
        self.assertFalse(has_transition_perm(manuscript.review, self.author))  
        self.assertFalse(has_transition_perm(submission3.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed): #can't submit twice
            submission3.submit(self.author)
        self.assertEqual(manuscript._status, m.Manuscript.Status.REVIEWING)

        #-------------- Create editor review (pass) -----------
        self.assertEqual(submission3._status, m.Submission.Status.IN_PROGRESS_EDITION)
        self.assertTrue(has_transition_perm(submission3.add_edition_noop, self.editor))
        edition3= m.Edition()
        edition3.submission = submission3
        edition3.save()
        self.assertTrue(has_transition_perm(edition3.edit_noop, self.editor))
        self.assertFalse(has_transition_perm(submission3.submit_edition, self.editor))
        edition3._status = m.Edition.Status.NO_ISSUES
        edition3.save()
        self.assertTrue(has_transition_perm(submission3.submit_edition, self.editor))
        submission3.submit_edition()
        submission3.save()
        self.assertEqual(submission3._status, m.Submission.Status.IN_PROGRESS_CURATION)

        #-------------- Create curation (fail) -----------
        self.assertEqual(submission3._status, m.Submission.Status.IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission3.add_curation_noop, self.curator))
        curation3 = m.Curation()
        curation3.submission = submission3
        curation3.save()
        self.assertTrue(has_transition_perm(curation3.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission3.review_curation, self.curator))
        curation3._status = m.Curation.Status.MINOR_ISSUES
        curation3.save()
        self.assertTrue(has_transition_perm(submission3.review_curation, self.curator))
        submission3.review_curation()
        submission3.save()
        self.assertEqual(submission3._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)

        #-------------- Create curator report -----------
        self.assertTrue(has_transition_perm(submission3.send_report, self.curator))
        submission3.send_report()
        submission3.save()
        self.assertEqual(submission3._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        #-------------- Create editor return -----------
        self.assertTrue(has_transition_perm(submission3.finish_submission, self.editor))
        submission3.finish_submission()
        submission3.save()
        self.assertEqual(submission3._status, m.Submission.Status.RETURNED)
        self.assertEqual(manuscript._status, m.Manuscript.Status.AWAITING_RESUBMISSION)

        #################### ROUND 4 #####################

        #-------------- Create submission ----------------
        self.assertFalse(has_transition_perm(manuscript.review, self.author))
        submission4 = m.Submission()
        submission4.manuscript = manuscript
        submission4.save()
        self.assertTrue(has_transition_perm(manuscript.review, self.author))  
        self.assertTrue(has_transition_perm(submission4.submit, self.author))   
        submission4.submit(self.author)
        submission4.save()
        self.assertFalse(has_transition_perm(manuscript.review, self.author))  
        self.assertFalse(has_transition_perm(submission4.submit, self.author))   
        with self.assertRaises(TransitionNotAllowed): #can't submit twice
            submission4.submit(self.author)

        #-------------- Create editor review (pass) -----------
        self.assertEqual(submission4._status, m.Submission.Status.IN_PROGRESS_EDITION)
        self.assertTrue(has_transition_perm(submission4.add_edition_noop, self.editor))
        edition4= m.Edition()
        edition4.submission = submission4
        edition4.save()
        self.assertTrue(has_transition_perm(edition4.edit_noop, self.editor))
        self.assertFalse(has_transition_perm(submission4.submit_edition, self.editor))
        edition4._status = m.Edition.Status.NO_ISSUES
        edition4.save()
        self.assertTrue(has_transition_perm(submission4.submit_edition, self.editor))
        submission4.submit_edition()
        submission4.save()
        self.assertEqual(submission4._status, m.Submission.Status.IN_PROGRESS_CURATION)

        #-------------- Create curation (pass) -----------
        self.assertEqual(submission4._status, m.Submission.Status.IN_PROGRESS_CURATION)
        self.assertTrue(has_transition_perm(submission4.add_curation_noop, self.curator))
        curation4 = m.Curation()
        curation4.submission = submission4
        curation4.save()
        self.assertTrue(has_transition_perm(curation4.edit_noop, self.curator))
        self.assertFalse(has_transition_perm(submission4.review_curation, self.curator))
        curation4._status = m.Curation.Status.NO_ISSUES
        curation4.save()
        self.assertTrue(has_transition_perm(submission4.review_curation, self.curator))
        submission4.review_curation()
        submission4.save()
        self.assertEqual(submission4._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)

        #--------- Create verification (pass) ------------
        self.assertEqual(submission4._status, m.Submission.Status.IN_PROGRESS_VERIFICATION)
        self.assertTrue(has_transition_perm(submission4.add_verification_noop, self.verifier))
        verification4 = m.Verification()
        verification4.submission = submission4
        verification4.save()
        self.assertTrue(has_transition_perm(verification4.edit_noop, self.verifier))
        self.assertFalse(has_transition_perm(submission4.review_verification, self.verifier))
        verification4._status = m.Verification.Status.SUCCESS
        verification4.save()
        self.assertTrue(has_transition_perm(submission4.review_verification, self.verifier))
        submission4.review_verification()
        submission4.save()
        self.assertEqual(submission4._status, m.Submission.Status.REVIEWED_AWAITING_REPORT)
        self.assertEqual(manuscript._status, m.Manuscript.Status.PROCESSING)

        #-------------- Create curator report -----------
        self.assertTrue(has_transition_perm(submission4.send_report, self.curator))
        submission4.send_report()
        submission4.save()
        self.assertEqual(submission4._status, m.Submission.Status.REVIEWED_REPORT_AWAITING_APPROVAL)

        #-------------- Create editor return -----------
        self.assertTrue(has_transition_perm(submission4.finish_submission, self.editor))
        submission4.finish_submission()
        submission4.save()
        self.assertEqual(submission4._status, m.Submission.Status.RETURNED)
        self.assertEqual(manuscript._status, m.Manuscript.Status.COMPLETED)