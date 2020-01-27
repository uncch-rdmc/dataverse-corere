from django.db import models
from django.contrib.auth.models import AbstractUser
from django_fsm import FSMField, transition
import logging

logger = logging.getLogger('corere')  

####################################################

class User(AbstractUser):
    # This model inherits these fields from abstract user:
    # username, email, first_name, last_name, date_joined and last_login, password, is_superuser, is_staff and is_active

    #NOTE: This approach won't scale great if we need real object-based permissions per manuscript.
    #      But the requirements for the group are pretty well-defined to these roles and this keeps things simple.
    is_author = models.BooleanField(default=False)
    is_editor = models.BooleanField(default=False)
    is_curator = models.BooleanField(default=False)
    is_verifier = models.BooleanField(default=False)

    #MAD: We probably need to manage relations between users. Editors will need to manage authors at least
    #     Is this going to be a direct connection, or via a "publication" object or something?
    #     Each editor will have multipe authors... and each author multiple editors?

####################################################

VERIFICATION_NEW = "new"
VERIFICATION_NOT_ATTEMPTED = "not_attempted" # The name of this is vague
VERIFICATION_MINOR_ISSUES = "minor_issues"
VERIFICATION_MAJOR_ISSUES = "major_issues"
VERIFICATION_SUCCESS_W_MOD = "success_w_mod"
VERIFICATION_SUCCESS = "success"

VERIFICATION_RESULT_CHOICES = (
    (VERIFICATION_NEW, 'New'),
    (VERIFICATION_NOT_ATTEMPTED, 'Not Attempted'),
    (VERIFICATION_MINOR_ISSUES, 'Minor Issues'),
    (VERIFICATION_MAJOR_ISSUES, 'Major Issues'),
    (VERIFICATION_SUCCESS_W_MOD, 'Success with Modification'),
    (VERIFICATION_SUCCESS, 'Success'),
)

class Verification(models.Model):
    status = FSMField(max_length=15, choices=VERIFICATION_RESULT_CHOICES, default=VERIFICATION_NEW)
    #result = models.CharField(max_length=15, choices=VERIFICATION_RESULT_CHOICES)
    note_text = models.TextField() #TODO: Make this more usable as a list of issues
    software = models.TextField() #TODO: Make this more usable as a list of software
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verifiers = models.ManyToManyField(User, related_name="verifier_verifications", blank=True)

####################################################

CURATION_NEW = 'new'
CURATION_INCOM_MATERIALS = 'incom_materials'
CURATION_MAJOR_ISSUES = 'major_issues'
CURATION_MINOR_ISSUES = 'minor_issues'
CURATION_NO_ISSUES = 'no_issues'

CURATION_RESULT_CHOICES = (
    (CURATION_NEW, 'New'),
    (CURATION_INCOM_MATERIALS, 'Incomplete Materials'),
    (CURATION_MAJOR_ISSUES, 'Major Issues'),
    (CURATION_MINOR_ISSUES, 'Minor Issues'),
    (CURATION_NO_ISSUES, 'No Issues'),
)
class Curation(models.Model):
    status = FSMField(max_length=15, choices=CURATION_RESULT_CHOICES, default=CURATION_NEW)
    #result = models.CharField(max_length=15, choices=CURATION_RESULT_CHOICES)
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    curators = models.ManyToManyField(User, related_name="curator_curations", blank=True)

####################################################

#Stores metadata
class File(models.Model):
    title = models.TextField()
    md5 = models.CharField(max_length=32)

class Submission(models.Model):
    #Submission does not have a result in itself, it is captured 
    files = models.ForeignKey(File, on_delete=models.CASCADE, related_name='files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    authors = models.ManyToManyField(User, related_name="author_submissions", blank=True)

####################################################

MANUSCRIPT_NEW = 'new' 
MANUSCRIPT_AWAITING = 'awaiting'
MANUSCRIPT_PROCESSING = 'processing'
MANUSCRIPT_COMPLETED = 'completed'

MANUSCRIPT_STATUS_CHOICES = (
    (MANUSCRIPT_NEW, 'New'),
    (MANUSCRIPT_AWAITING, 'Awaiting Submission'),
    (MANUSCRIPT_PROCESSING, 'Processing Submission'),
    (MANUSCRIPT_COMPLETED, 'Completed'),
)

class Manuscript(models.Model):
    pub_id = models.CharField(max_length=200, default="", db_index=True)
    title = models.TextField(blank=False, null=False, default="")
    note_text = models.TextField(default="")
    doi = models.CharField(max_length=200, default="", db_index=True)
    open_data = models.BooleanField(default=False)
    submissions = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="submissions", blank=True, null=True)
    verifications = models.ForeignKey(Verification, on_delete=models.CASCADE, related_name="verifications", blank=True, null=True)
    curations = models.ForeignKey(Curation, on_delete=models.CASCADE, related_name="curations", blank=True, null=True)
    status = FSMField(max_length=10, choices=MANUSCRIPT_STATUS_CHOICES, default=MANUSCRIPT_NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    editors = models.ManyToManyField(User, related_name="editor_manuscripts", blank=True)

    ### django-fsm (workflow) related functions

    def can_begin(self):
        if(self.editors.count() == 0):
            return False
        return True

    @transition(field=status, source=MANUSCRIPT_NEW, target=MANUSCRIPT_AWAITING, conditions=[can_begin], 
                permission=lambda instance, user: user.is_curator)
    def begin(self):
        #Here add any additional actions related to the state change
        pass
