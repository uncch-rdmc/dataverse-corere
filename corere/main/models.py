from django.db import models
from django.contrib.auth.models import AbstractUser
from django_fsm import FSMField, transition
from corere.main import constants as c
from guardian.shortcuts import get_users_with_perms
import logging
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger('corere')  
####################################################

class AbstractCreateUpdateModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="creator_%(class)ss", blank=True, null=True)
    last_editor = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="last_editor_%(class)ss", blank=True, null=True)

    class Meta:
        abstract = True

    #TODO: Set up saving creator/editor, see https://www.agiliq.com/blog/2019/01/tracking-creator-of-django-objects/
        
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

class Verification(AbstractCreateUpdateModel):
    status = FSMField(max_length=15, choices=VERIFICATION_RESULT_CHOICES, default=VERIFICATION_NEW)
    software = models.TextField() #TODO: Make this more usable as a list of software
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_verifications", blank=True, null=True)

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
class Curation(AbstractCreateUpdateModel):
    status = FSMField(max_length=15, choices=CURATION_RESULT_CHOICES, default=CURATION_NEW)
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_curations", blank=True, null=True)

####################################################

class Submission(AbstractCreateUpdateModel):
    #Submission does not have a result in itself, it is captured 
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_submissions", blank=True, null=True)

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

class Manuscript(AbstractCreateUpdateModel):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) #currently only used for naming a file folder on upload. Needed as id doesn't exist until after create
    pub_id = models.CharField(max_length=200, default="", db_index=True)
    title = models.TextField(blank=False, null=False, default="")
    note_text = models.TextField(default="")
    doi = models.CharField(max_length=200, default="", db_index=True)
    open_data = models.BooleanField(default=False)
    status = FSMField(max_length=10, choices=MANUSCRIPT_STATUS_CHOICES, default=MANUSCRIPT_NEW)

    def __str__(self):
        return '{0}: {1}'.format(self.id, self.title)

    class Meta:
        permissions = [
            ('manage_authors_on_manuscript', 'Can manage authors on manuscript')
        ]

    ### django-fsm (workflow) related functions

    #Conditions
    # - Authors needed
    # - files uploaded (maybe)?
    def can_begin(self):
        # Are there any authors assigned to the manuscript?
        group_string = name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.id)
        count = User.objects.filter(groups__name=group_string).count()
        if(count < 1):
            return False
        return True

    #MAD: I'm not sure begin is even real?
    @transition(field=status, source=MANUSCRIPT_NEW, target=MANUSCRIPT_AWAITING, conditions=[can_begin],
                permission=lambda instance, user: user.groups.filter(name='c.GROUP_ROLE_VERIFIER').exists())
    def begin(self):
        #Here add any additional actions related to the state change
        pass

####################################################

# See this blog post for info on why these models don't use GenericForeign Key (implementation #1 chosen)
# https://lukeplant.me.uk/blog/posts/avoid-django-genericforeignkey/


FILE_TYPE_MANUSCRIPT = 'manuscript'
FILE_TYPE_APPENDIX = 'appendix'
FILE_TYPE_OTHER = 'other'

FILE_TYPE_CHOICES = (
    (FILE_TYPE_MANUSCRIPT, 'Manuscript'),
    (FILE_TYPE_APPENDIX, 'Appendix'),
    (FILE_TYPE_OTHER, 'Other'),
)

#TODO: This needs rework. Do we still need manuscript UUID? Does instance.owner.id work? Should we be using slugs?
def manuscript_directory_path(instance, filename):
    return 'manuscript_{0}/{1}_{2}/{3}'.format(instance.owner.manuscript.uuid, instance.owner._meta.model_name, instance.owner.id, filename)

class File(AbstractCreateUpdateModel):
    file = models.FileField(upload_to=manuscript_directory_path, blank=True) #TODO: Redo path, currently blows up because it uses manuscript uuid
    type = models.CharField(max_length=12, choices=FILE_TYPE_CHOICES, default=FILE_TYPE_OTHER) 

    owner_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE)
    owner_curation = models.ForeignKey(Curation, null=True, blank=True, on_delete=models.CASCADE)
    owner_verification = models.ForeignKey(Verification, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def owner(self):
        if self.owner_submission_id is not None:
            return self.owner_submission
        if self.owner_curation_id is not None:
            return self.owner_curation
        if self.owner_verification_id is not None:
            return self.owner_verification
        raise AssertionError("Neither 'owner_submission', 'owner_curation' or 'owner_verification' is set")

    def save(self, *args, **kwargs):
        owners = 0
        owners += (self.owner_submission_id is not None)
        owners += (self.owner_curation_id is not None)
        owners += (self.owner_verification_id is not None)
        if(owners > 1):
            raise AssertionError("Multiple owners set")
        super(File, self).save(*args, **kwargs)

class Notes(AbstractCreateUpdateModel):
    text = models.TextField(default="")

    owner_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE)
    owner_curation = models.ForeignKey(Curation, null=True, blank=True, on_delete=models.CASCADE)
    owner_verification = models.ForeignKey(Verification, null=True, blank=True, on_delete=models.CASCADE)
    owner_file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def owner(self):
        if self.owner_submission_id is not None:
            return self.owner_submission
        if self.owner_curation_id is not None:
            return self.owner_curation
        if self.owner_verification_id is not None:
            return self.owner_verification
        if self.owner_file_id is not None:
            return self.owner_file
        raise AssertionError("Neither 'owner_submission', 'owner_curation', 'owner_verification' or 'owner_file' is set")
    
    def save(self, *args, **kwargs):
        owners = 0
        owners += (self.owner_submission_id is not None)
        owners += (self.owner_curation_id is not None)
        owners += (self.owner_verification_id is not None)
        if(owners > 1):
            raise AssertionError("Multiple owners set")
        super(Notes, self).save(*args, **kwargs)