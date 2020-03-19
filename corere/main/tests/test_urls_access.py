import json
import unittest
from django.test import TestCase
from corere.main.middleware import local
from django.db.utils import IntegrityError
from django.db import transaction
from corere.main import models as m
from corere.main import constants as c
from django.core.exceptions import FieldError
from django.contrib.auth.models import Permission, Group

# Do I need to use a mock for my tests?
# If not IDs are going to get bumped so I probably should
# I really just want one Manuscript/Submission/Curation/Verification/Note for now
# TODO: Should you really be able to directly set the the status?
@unittest.skip("Don't want to test")
class TestModels(TestCase):
    def setUp(self):
        self.user = m.User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        local.user = self.user #needed for middleware that saves creator/updater

    #This tests ensures that manuscripts/submissions/curations/verifications/notes can be created.
    #Furthermore, it tests the restrictions related to creating and connecting these objects.
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
        submission.save()
        sub_t = m.Submission.objects.get(id=submission.id)
        self.assertEqual(submission, sub_t)
        sub_note = m.Note()
        sub_note.parent_submission = submission
        sub_note.save()
        sub_note_t = m.Note.objects.get(id=sub_note.id)
        self.assertEqual(sub_note, sub_note_t)

        with self.assertRaises(FieldError) as exc_sub2, transaction.atomic():
            submission2bad = m.Submission()
            submission2bad.manuscript = manuscript
            submission2bad.save()
        self.assertTrue('A submission is already in progress for this manuscript' in str(exc_sub2.exception))

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

    #Test general note restrictions not covered in the objects test
    #TODO: Include manuscript and files when available
    #TODO: Do this later, right now I'm worried we'll add more restrictions on the normal flow
    #def test_notes(self):
        #no more than one sub/cur/ver
        #you can't put a something in the wrong slot
        #you can't create a note without one?

class TestManuscriptWorkflow(TestCase):
    def setUp(self):
        self.editor = m.User.objects.create_user('editor') #gotta have a user to create a manuscript
        local.user = self.editor #we will change this as different users edit the objects
        self.manuscript = m.Manuscript()
        self.manuscript.save()
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.editor)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.editor)
        
        self.author = m.User.objects.create_user('author')
        Group.objects.get(name=c.GROUP_ROLE_AUTHOR).user_set.add(self.author)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.author)

        self.curator = m.User.objects.create_user('curator')
        Group.objects.get(name=c.GROUP_ROLE_CURATOR).user_set.add(self.curator)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.curator)

        self.verifier = m.User.objects.create_user('verifier')
        Group.objects.get(name=c.GROUP_ROLE_VERIFIER).user_set.add(self.verifier)
        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).user_set.add(self.verifier)

    #MAD: So... I want this testing workflow directly? Do I want to also check various url access throughout?
    #Seems like it'll get too complicated. I want to test with the workflow that other users can't progress the flow
    #So maybe I should create a separate test for urls
    @unittest.skip("Don't want to test")
    def test_basic_manuscript_cycle_and_permisssions_direct(self):
        local.user = self.author
        submission = m.Submission()
        submission.manuscript = self.manuscript
        submission.save()    

        self.assertTrue(True)

    @unittest.skip("Don't want to test")
    def test_basic_manuscript_cycle_and_permisssions_via_url(self):
        pass