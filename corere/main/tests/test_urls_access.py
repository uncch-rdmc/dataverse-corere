import json
import unittest
from django.test import TestCase
from corere.main.middleware import local
from django.db.utils import IntegrityError
from django.db import transaction
from corere.main import models as m
from django.core.exceptions import FieldError

# Do I need to use a mock for my tests?
# If not IDs are going to get bumped so I probably should
# I really just want one Manuscript/Submission/Curation/Verification/Note for now

class TestWorkflowSuperuser(TestCase):
    def setUp(self):
        self.user = m.User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
        local.user = self.user #needed for middleware that saves creator/updater

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

        submission.status = m.SUBMISSION_IN_PROGRESS_CURATION
        submission.save()
        curation.save()
        cur_t = m.Curation.objects.get(id=curation.id)
        self.assertEqual(curation, cur_t)

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
        
        submission.status = m.SUBMISSION_IN_PROGRESS_VERIFICATION
        submission.save()
        verification.save()
        ver_t = m.Verification.objects.get(id=verification.id)
        self.assertEqual(verification, ver_t)

        with self.assertRaises(IntegrityError) as exc_ver3, transaction.atomic():
            verification2bad = m.Verification()
            verification2bad.submission = submission
            verification2bad.save()
        print(str(exc_ver3.exception))
        self.assertTrue('duplicate key value violates unique constraint "main_verification_submission_id_key"' in str(exc_ver3.exception))

#DO: Add field errors to curation and verification
#    Break up these tests to one per object