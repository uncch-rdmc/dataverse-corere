from django.db import models
from django.contrib.auth.models import AbstractUser
from django_fsm import FSMField, transition
import logging
import uuid

logger = logging.getLogger('corere')  

####################################################

class User(AbstractUser):
    # This model inherits these fields from abstract user:
    # username, email, first_name, last_name, date_joined and last_login, password, is_superuser, is_staff and is_active

    # See apps.py/signals.py for the instantiation of CoReRe's default User groups/permissions

    invite_key = models.CharField(max_length=64, blank=True) # MAD: Should this be encrypted?
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

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


def manuscript_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/manuscript_<uuid>/<filename>
    return 'manuscript_{0}/{1}'.format(instance.uuid, filename)

class Manuscript(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) #currently only used for naming a file folder on upload. Needed as id doesn't exist until after create
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
    manuscript_file = models.FileField(upload_to=manuscript_directory_path, blank=True)

    def __str__(self):
        return '{0}: {1}'.format(self.id, self.title)

    class Meta:
        permissions = [
            ('manage_authors_on_manuscript', 'Can manage authors on manuscript')
        ]

    ### django-fsm (workflow) related functions

    # TODO: This breaks
    def can_begin(self):
        if(self.editors.count() == 0):
            return False
        return True

    @transition(field=status, source=MANUSCRIPT_NEW, target=MANUSCRIPT_AWAITING, conditions=[can_begin], 
                permission=lambda instance, user: user.is_curator)
    def begin(self):
        #Here add any additional actions related to the state change
        pass
