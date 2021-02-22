import logging
import uuid
# from . import constants as c
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import FieldError
from django_fsm import FSMField, transition, RETURN_VALUE, has_transition_perm, TransitionNotAllowed
from django.db.models import Q, Max
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_delete
from guardian.shortcuts import get_users_with_perms, assign_perm
from simple_history.models import HistoricalRecords
from simple_history.utils import update_change_reason
from corere.main import constants as c
from corere.main import git as g
from corere.main.middleware import local
from corere.main.utils import fsm_check_transition_perm
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_group, get_perms
from autoslug import AutoSlugField

logger = logging.getLogger(__name__)  
####################################################

class AbstractCreateUpdateModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='created at', help_text='Date model was created')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='updated at', help_text='Date model was last updated')
    creator = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="creator_%(class)ss", blank=True, null=True, verbose_name='Creator User')
    last_editor = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="last_editor_%(class)ss", blank=True, null=True, verbose_name='Last Updating User')

    def save(self, *args, **kwargs):
        if hasattr(local, 'user'):
            if(self.pk is None):
                self.creator = local.user
            else:
                self.last_editor = local.user
        return super(AbstractCreateUpdateModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True

# Adding an additional field to our histories for changes. We populate this after save with a post_save signal        
class AbstractHistoryWithChanges(models.Model):
    history_change_list = models.TextField(blank=False, null=False, default="")

    class Meta:
        abstract = True

####################################################

class User(AbstractUser):
    # This model inherits these fields from abstract user:
    # username, email, first_name, last_name, date_joined and last_login, password, is_superuser, is_staff and is_active

    # See apps.py/signals.py for the instantiation of CoReRe's default User groups/permissions

    invite_key = models.CharField(max_length=64, blank=True) # MAD: Should this be encrypted?
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

    # Django Guardian has_perm does not check whether the user has a global perm.
    # We always want that in our project, so this function checks both
    # See for more info: https://github.com/django/django/pull/9581
    def has_any_perm(self, perm_string, obj):
        return self.has_perm(c.perm_path(perm_string)) or self.has_perm(perm_string, obj)

####################################################

class Edition(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = 'new', _('New')
        ISSUES = 'issues', _('Issues')
        NO_ISSUES = 'no_issues', _('No Issues')

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Editor Approval', help_text='Was the submission approved by the editor')
    report = models.TextField(default="", blank=True, verbose_name='Report')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_edition')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_edition")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(self.submission._status != Submission.Status.IN_PROGRESS_EDITION):
                raise FieldError('A edition cannot be added to a submission unless its status is: ' + Submission.Status.IN_PROGRESS_EDITION)
        except Edition.submission.RelatedObjectDoesNotExist:
            pass #this is caught in super
        try:
            self.manuscript #to see if not set
        except Edition.manuscript.RelatedObjectDoesNotExist:
            self.manuscript = self.submission.manuscript
        super(Edition, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    def can_edit(self):
        if(self.submission._status == Submission.Status.IN_PROGRESS_EDITION ):
            return True
        return False

    #approve_manuscript_submissions
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[can_edit],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_APPROVE, instance.submission.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------
    
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance.submission._status == Submission.Status.IN_PROGRESS_EDITION and user.has_any_perm(c.PERM_MANU_APPROVE,instance.submission.manuscript))
                                            or (instance.submission._status != Submission.Status.IN_PROGRESS_EDITION and user.has_any_perm(c.PERM_MANU_VIEW_M,instance.submission.manuscript))) )
    def view_noop(self):
        return self._status

####################################################

class Curation(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = 'new', _('New')
        INCOM_MATERIALS = 'incom_materials', _('Incomplete Materials')
        MAJOR_ISSUES = 'major_issues', _('Major Issues')
        MINOR_ISSUES = 'minor_issues', _('Minor Issues')
        NO_ISSUES = 'no_issues', _('No Issues')

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Curation Status', help_text='Was the submission approved by the curator')
    report = models.TextField(default="", blank=True, verbose_name='Report')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_curation')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_curation")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(self.submission._status != Submission.Status.IN_PROGRESS_CURATION):
                raise FieldError('A curation cannot be added to a submission unless its status is: ' + Submission.Status.IN_PROGRESS_CURATION)
        except Curation.submission.RelatedObjectDoesNotExist:
            pass #this is caught in super
        try:
            self.manuscript #to see if not set
        except Curation.manuscript.RelatedObjectDoesNotExist:
            self.manuscript = self.submission.manuscript
        super(Curation, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    def can_edit(self):
        if(self.submission._status == Submission.Status.IN_PROGRESS_CURATION ):
            return True
        return False

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[can_edit],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_CURATE, instance.submission.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------
    
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance.submission._status == Submission.Status.IN_PROGRESS_CURATION and user.has_any_perm(c.PERM_MANU_CURATE,instance.submission.manuscript))
                                            or (instance.submission._status != Submission.Status.IN_PROGRESS_CURATION and user.has_any_perm(c.PERM_MANU_VIEW_M,instance.submission.manuscript))) )
    def view_noop(self):
        return self._status

####################################################

class Verification(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = "new"
        NOT_ATTEMPTED = "not_attempted" # The name of this is vague
        MINOR_ISSUES = "minor_issues"
        MAJOR_ISSUES = "major_issues"
        SUCCESS_W_MOD = "success_w_mod"
        SUCCESS = "success"

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Verification Status', help_text='Was the submission able to be verified')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_verification')
    report = models.TextField(default="", blank=True, verbose_name='Report')
    code_executability = models.CharField(max_length=2000, default="", verbose_name='Code Executability')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_verification")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(self.submission._status != Submission.Status.IN_PROGRESS_VERIFICATION):
                raise FieldError('A verification cannot be added to a submission unless its status is: ' + Submission.Status.IN_PROGRESS_VERIFICATION)
        except Verification.submission.RelatedObjectDoesNotExist:
            pass #this is caught in super
        try:
            self.manuscript #to see if not set
        except Verification.manuscript.RelatedObjectDoesNotExist:
            self.manuscript = self.submission.manuscript

        # if(not self.manuscript):
        #     self.manuscript = self.submission.manuscript
        super(Verification, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    def can_edit(self):
        if(self.submission._status == Submission.Status.IN_PROGRESS_VERIFICATION ):
            return True
        return False

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[can_edit],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_VERIFY, instance.submission.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance.submission._status == Submission.Status.IN_PROGRESS_VERIFICATION and user.has_any_perm(c.PERM_MANU_VERIFY,instance.submission.manuscript))
                                            or (instance.submission._status != Submission.Status.IN_PROGRESS_VERIFICATION and user.has_any_perm(c.PERM_MANU_VIEW_M,instance.submission.manuscript))) )
    def view_noop(self):
        return self._status

####################################################

#TODO: We should probably have a "uniqueness" check on the object level for submissions incase two users click submit at the same time.
#Our views do check transition permissions first so it'd have to be at the exact same time.
#May also be needed for curation/verification, otherwise you may end up with one that is an orphan.
class Submission(AbstractCreateUpdateModel):
    # Before we were just doing new/submitted as technically you can learn the status of the submission from its attached curation/verification.
    # But its much easier to find out if any submissions are in progress this way. Maybe we'll switch back to the single point of truth later.
    class Status(models.TextChoices):
        NEW = 'new'
        IN_PROGRESS_EDITION = 'in_progress_edition'
        IN_PROGRESS_CURATION = 'in_progress_curation'
        IN_PROGRESS_VERIFICATION = 'in_progress_verification'
        REVIEWED_AWAITING_REPORT = 'reviewed_awaiting_report'
        REVIEWED_REPORT_AWAITING_APPROVAL = 'reviewed_awaiting_approve'
        RETURNED = 'returned'

    _status = FSMField(max_length=25, choices=Status.choices, default=Status.NEW, verbose_name='Submission review status', help_text='The status of the submission in the review process')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_submissions")
    version_id = models.IntegerField(verbose_name='Version number')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

    high_performance = models.BooleanField(default=False, verbose_name='Does this submission require a high-performance compute environment?')
    contents_gis = models.BooleanField(default=False, verbose_name='Does this submission contain GIS data and mapping?')
    contents_proprietary = models.BooleanField(default=False, verbose_name='Does this submission contain restricted or proprietary data?')
    contents_proprietary_sharing = models.BooleanField(default=False, verbose_name='Are you restricted from sharing this data with Odum for verification only?')
    
    class Meta:
        default_permissions = ()
        ordering = ['version_id']
        unique_together = ('manuscript', 'version_id',)

    def save(self, *args, **kwargs):
        prev_max_version_id = Submission.objects.filter(manuscript=self.manuscript).aggregate(Max('version_id'))['version_id__max']
        first_save = False
        if not self.pk: #only first save. Nessecary for submission in progress check but also to allow admin editing of submissions
            first_save = True
            try:
                if(Submission.objects.filter(manuscript=self.manuscript).exclude(_status=self.Status.RETURNED).count() > 0):
                    raise FieldError('A submission is already in progress for this manuscript')
                if self.manuscript._status != Manuscript.Status.AWAITING_INITIAL and self.manuscript._status != Manuscript.Status.AWAITING_RESUBMISSION:
                    raise FieldError('A submission cannot be created unless a manuscript status is set to await it')
            except Submission.manuscript.RelatedObjectDoesNotExist:
                pass #this is caught in super

            if prev_max_version_id is None:
                self.version_id = 1
            else:
                self.version_id = prev_max_version_id + 1

        super(Submission, self).save(*args, **kwargs)
        if(self.version_id > 1):
            prev_submission = Submission.objects.get(manuscript=self.manuscript, version_id=prev_max_version_id)
            for gfile in prev_submission.submission_files.all():
                new_gfile = gfile
                new_gfile.parent_submission = self
                new_gfile.id = None
                new_gfile.save()

    ##### Queries #####

    #We check an author is public (for both functions) by checking if the author group can view. This is based on the assumption that we always assign editor the same view permissions as author.
    def get_public_curator_notes(self):
        public_notes = []
        for note in Note.objects.filter(parent_submission=self, ref_cycle=Note.RefCycle.CURATION):#self.notes:
            note_perms = get_perms(Group.objects.get(name=c.GROUP_ROLE_AUTHOR), note)
            if 'view_note' in note_perms:
                public_notes.append(note)
        return public_notes

    def get_public_verifier_notes(self):
        public_notes = []
        for note in Note.objects.filter(parent_submission=self, ref_cycle=Note.RefCycle.VERIFICATION):#self.notes:
            note_perms = get_perms(Group.objects.get(name=c.GROUP_ROLE_AUTHOR), note)
            if 'view_note' in note_perms:
                public_notes.append(note)
        return public_notes

    ##### django-fsm (workflow) related functions #####

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=Status.NEW, target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance._status == instance.Status.NEW and user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript))
                                            or (instance._status != instance.Status.NEW and user.has_any_perm(c.PERM_MANU_VIEW_M, instance.manuscript))) )
    def view_noop(self):
        return self._status

    #-----------------------

    def can_submit(self):
        return True

    @transition(field=_status, source=Status.NEW, target=Status.IN_PROGRESS_EDITION, on_error=Status.NEW, conditions=[can_submit],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript)) #MAD: Used same perm as add, do we want that?
    def submit(self, user):
        if has_transition_perm(self.manuscript.review, user): #checking here because we need the user
            self.manuscript.review()
            self.manuscript.save()
        else:
            raise Exception
        pass

    #-----------------------

    def can_add_edition(self):
        if(self.manuscript._status != Manuscript.Status.REVIEWING):   
            return False
        if(Edition.objects.filter(submission=self).count() > 0): #Using a query because its ok if a new object exists but isn't saved
            return False
        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.IN_PROGRESS_EDITION], target=RETURN_VALUE(), conditions=[can_add_edition],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_APPROVE,instance.manuscript))
    #TODO: We should actually add the edition to the submission via a parameter instead of being a noop. Also do similar in other places
    def add_edition_noop(self):
        return self._status

    #-----------------------

    def can_add_curation(self):
        if(self.manuscript._status != Manuscript.Status.PROCESSING):   
            return False
        if(Curation.objects.filter(submission=self).count() > 0): #Using a query because its ok if a new object exists but isn't saved
            return False

        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.IN_PROGRESS_CURATION], target=RETURN_VALUE(), conditions=[can_add_curation],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_CURATE, instance.manuscript))
    #TODO: We should actually add the curation to the submission via a parameter instead of being a noop. Also do similar in other places
    def add_curation_noop(self):
        return self._status

    #-----------------------

    def can_add_verification(self):
        if(self.manuscript._status != Manuscript.Status.PROCESSING):       
            return False
        try:
            if(self.submission_curation._status != Curation.Status.NO_ISSUES):
                #print("The curation had issues, so shouldn't be verified")
                return False
        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return False
        if(Verification.objects.filter(submission=self).count() > 0): #Using a query because its ok if a new object exists but isn't saved
            return False
        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.IN_PROGRESS_VERIFICATION], target=RETURN_VALUE(), conditions=[can_add_verification],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_VERIFY, instance.manuscript))
    def add_verification_noop(self):
        return self._status

    #-----------------------

    #TODO: Change name?
    def can_submit_edition(self):
        #Note, the logic in here is decided whether you can even do a review, not whether its accepted
        try:
            if(self.submission_edition._status == Edition.Status.NEW):
                return False
        except Submission.submission_edition.RelatedObjectDoesNotExist:
            return False
        return True

    @transition(field=_status, source=[Status.IN_PROGRESS_EDITION], target=RETURN_VALUE(), conditions=[can_submit_edition],
                permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_APPROVE,instance.manuscript)))
    def submit_edition(self):
        #TODO: Call manuscript.process
        if(self.submission_edition._status == Edition.Status.NO_ISSUES):
            self.manuscript.process()
            self.manuscript.save()
            return self.Status.IN_PROGRESS_CURATION
        else:
            g.create_submission_branch(self) #We create the submission branch before returning the submission, to "save" the current state of the repo for history
            self.manuscript._status = Manuscript.Status.AWAITING_RESUBMISSION
            self.manuscript.save()
            return self.Status.RETURNED

    #-----------------------

    def can_review_curation(self):
        try:
            if(self.submission_curation._status == Curation.Status.NEW):
                return False
        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return False
        return True

    @transition(field=_status, source=[Status.IN_PROGRESS_CURATION], target=RETURN_VALUE(), conditions=[can_review_curation],
                permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_CURATE, instance.manuscript)))
    def review_curation(self):
        try:
            if(self.submission_curation._status == Curation.Status.NO_ISSUES):
                return self.Status.IN_PROGRESS_VERIFICATION
        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return self.Status.IN_PROGRESS_CURATION
        
        g.create_submission_branch(self) #We create the submission branch before returning the submission, to "save" the current state of the repo for history
        return self.Status.REVIEWED_AWAITING_REPORT

    #-----------------------

    def can_review_verification(self):
        try:
            if(self.submission_verification._status == Verification.Status.NEW):
                return False
        except Submission.submission_verification.RelatedObjectDoesNotExist:
            return False
        return True

    @transition(field=_status, source=[Status.IN_PROGRESS_VERIFICATION], target=RETURN_VALUE(), conditions=[can_review_verification],
                permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_VERIFY, instance.manuscript)))
    def review_verification(self):
        try:
            if(self.submission_verification._status == Verification.Status.SUCCESS): #just checking the object exists, crude
                pass
        except Submission.submission_verification.RelatedObjectDoesNotExist:
            return self.Status.IN_PROGRESS_VERIFICATION
        
        g.create_submission_branch(self) #We create the submission branch before returning the submission, to "save" the current state of the repo for history
        return self.Status.REVIEWED_AWAITING_REPORT

    #-----------------------
    
    def can_generate_report(self):
        return True

    @transition(field=_status, source=Status.REVIEWED_AWAITING_REPORT, target=Status.REVIEWED_REPORT_AWAITING_APPROVAL, conditions=[can_generate_report],
            permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_CURATE, instance.manuscript)))
    def generate_report(self):
        pass

    #-----------------------
    
    #TODO: It would be better to have this logic as a manuscript transition. 
    # Its somewhat annoying to get to the latest submission from the manuscript, so for now it'll remain here.
    def can_return_submission(self):
        return True

    @transition(field=_status, source=Status.REVIEWED_REPORT_AWAITING_APPROVAL, target=Status.RETURNED, conditions=[can_return_submission],
            permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_APPROVE, instance.manuscript)))
    def return_submission(self):
        if(self.submission_curation._status == Curation.Status.NO_ISSUES):
            if(self.submission_verification._status == Verification.Status.SUCCESS):
                self.manuscript._status = Manuscript.Status.COMPLETED
                ## We decided to leave completed manuscripts in the list and toggle their visibility
                # Delete existing groups when done for clean-up and reporting
                # Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).delete()
                # Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).delete()
                # Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).delete()
                # Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).delete()

                self.manuscript.save()
                return
            
        self.manuscript._status = Manuscript.Status.AWAITING_RESUBMISSION
        self.manuscript.save()
        return

####################################################

class Author(models.Model):
    class IdScheme(models.TextChoices):
        ORCID = 'ORCID', _('ORCID') 
        ISNI = 'ISNI', _('ISNI')
        LCNA = 'LCNA', _('LCNA')
        VIAF = 'VIAF', _('VIAF')
        GND = 'GND', _('GND')
        DAI = 'DAI', _('DAI')
        REID = 'ResearcherID', _('ResearcherID')
        SCID = 'ScopusID', _('ScopusID')

    first_name = models.CharField(max_length=150, blank=False, null=False,  verbose_name='First Name')
    last_name =  models.CharField(max_length=150, blank=False, null=False,  verbose_name='Last Name')
    identifier_scheme = models.CharField(max_length=14, blank=True, null=True,  choices=IdScheme.choices, verbose_name='Identifier Scheme') 
    identifier = models.CharField(max_length=150, blank=True, null=True, verbose_name='Identifier')
    position = models.IntegerField(verbose_name='Position', help_text='Position/order of the author in the list of authors')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_authors")

class DataSource(models.Model):
    text = models.CharField(max_length=200, blank=False, null=False, default="", verbose_name='Data Source')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_data_sources")

class Keyword(models.Model):
    text = models.CharField(max_length=200, blank=False, null=False, default="", verbose_name='Keyword')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_keywords")

####################################################

class Manuscript(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = 'new', _('New')
        AWAITING_INITIAL = 'awaiting_init', _('Awaiting Initial Submission')
        AWAITING_RESUBMISSION = 'awaiting_resub', _('Awaiting Resubmission')
        REVIEWING = 'reviewing', _('Reviewing Submission')
        PROCESSING = 'processing', _('Processing Submission')
        COMPLETED = 'completed', _('Completed')

    class Subjects(models.TextChoices):
        AGRICULTURAL = 'agricultural', _('Agricultural Sciences')
        ARTS_AND_HUMANITIES = 'arts', _('Arts and Humanities')
        ASTRONOMY_ASTROPHYSICS = 'astronomy', _('Astronomy and Astrophysics')
        BUSINESS_MANAGEMENT = 'business', _('Business and Management')
        CHEMISTRY = 'chemistry', _('Chemistry')
        COMPUTER_INFORMATION = 'computer', _('Computer and Information Science')
        ENVIRONMENTAL = 'environmental', _('Earth and Environmental Sciences')
        ENGINEERING = 'engineering', _('Engineering')
        LAW = 'law', _('Law')
        MATHEMATICS = 'mathematics', _('Mathematical Sciences')
        HEALTH = 'health', _('Medicine, Health and Life Sciences')
        PHYSICS = 'physics', _('Physics')
        SOCIAL = 'social', _('Social Sciences')
        OTHER = 'other', _('Other')

    title = models.CharField(max_length=200, default="", verbose_name='Manuscript Title', help_text='Title of the manuscript')
    pub_id = models.CharField(max_length=200, default="", blank=True, null=True, db_index=True, verbose_name='Publication ID', help_text='The internal ID from the publication')
    qual_analysis = models.BooleanField(default=False, blank=True, null=True, verbose_name='Qualitative Analysis', help_text='Whether this manuscript needs qualitative analysis')
    qdr_review = models.BooleanField(default=False, blank=True, null=True, verbose_name='QDR Review', help_text='Was this manuscript reviewed by the Qualitative Data Repository?')
    contact_first_name = models.CharField(max_length=150, blank=True, verbose_name='Contact First Name', help_text='First name of the publication contact that will be stored in Dataverse')
    contact_last_name =  models.CharField(max_length=150, blank=True, verbose_name='Contact last Name', help_text='Last name of the publication contact that will be stored in Dataverse')
    contact_email = models.EmailField(blank=True, null=True, verbose_name='Contact Email Address', help_text='Email address of the publication contact that will be stored in Dataverse')
    dataverse_doi = models.CharField(max_length=150, blank=True, verbose_name='Dataverse DOI', help_text='DOI of the publication in Dataverse')
    description = models.CharField(max_length=1024, blank=True, null=True, default="", verbose_name='Description', help_text='Additional info about the manuscript')
    subject = models.CharField(max_length=14, blank=True, null=True, choices=Subjects.choices, verbose_name='Subject') 
    producer_first_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Producer First Name')
    producer_last_name =  models.CharField(max_length=150, blank=True, null=True, verbose_name='Producer Last Name')
    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Manuscript Status', help_text='The overall status of the manuscript in the review process')
     
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) #currently only used for naming a file folder on upload. Needed as id doesn't exist until after create
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,], excluded_fields=['slug'])
    slug = AutoSlugField(populate_from='title')

    class Meta:
        permissions = [
            #TODO: This includes default CRUD permissions. We could switch it to be explicit (other objects too)
            (c.PERM_MANU_ADD_AUTHORS, 'Can manage authors on manuscript'),
            (c.PERM_MANU_REMOVE_AUTHORS, 'Can manage authors on manuscript'), # we needed more granularity for authors
            (c.PERM_MANU_MANAGE_EDITORS, 'Can manage editors on manuscript'),
            (c.PERM_MANU_MANAGE_CURATORS, 'Can manage curators on manuscript'),
            (c.PERM_MANU_MANAGE_VERIFIERS, 'Can manage verifiers on manuscript'),
            (c.PERM_MANU_ADD_SUBMISSION, 'Can add submission to manuscript'),
            #('review_submission_on_manuscript', 'Can review submission on manuscript'),
            # We track permissions of objects under the manuscript at the manuscript level, as we don't need to be more granular
            # Technically curation/verification are added to a submission
            (c.PERM_MANU_APPROVE, 'Can review submissions for processing'),
            (c.PERM_MANU_CURATE, 'Can curate manuscript/submission'),
            (c.PERM_MANU_VERIFY, 'Can verify manuscript/submission'),
        ]

    def __str__(self):
        return '{0}: {1}'.format(self.id, self.title)

    def save(self, *args, **kwargs):
        first_save = False
        if not self.pk:
            first_save = True
        super(Manuscript, self).save(*args, **kwargs)
        if first_save:
            # Note these works alongside global permissions defined in signals.py
            # TODO: Make this concatenation standardized
            group_manuscript_editor, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.id))
            assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_DELETE_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_ADD_AUTHORS, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_APPROVE, group_manuscript_editor, self)

            group_manuscript_author, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.id))
            #assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_author, self)
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_author, self) 
            assign_perm(c.PERM_MANU_ADD_AUTHORS, group_manuscript_author, self) 
            assign_perm(c.PERM_MANU_ADD_SUBMISSION, group_manuscript_author, self) 

            group_manuscript_curator, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.id))
            assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_curator, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_curator, self) 
            assign_perm(c.PERM_MANU_CURATE, group_manuscript_curator, self) 

            group_manuscript_verifier, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.id))
            #assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_verifier, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_verifier, self) 
            assign_perm(c.PERM_MANU_VERIFY, group_manuscript_verifier, self) 

            group_manuscript_editor.user_set.add(local.user) #TODO: Should be dynamic on role or more secure, but right now only editors create manuscripts

            g.create_manuscript_repo(self)
            g.create_submission_repo(self)

    def is_complete(self):
        return self._status == Manuscript.Status.COMPLETED
            
    ##### django-fsm (workflow) related functions #####
    
    #Extra function defined so fsm errors can be passed to use when submitting a form.
    #Conditions: Authors needed, files uploaded [NOT DONE]
    def can_begin_return_problems(self):
        problems = []
        # Are there any authors assigned to the manuscript?
        group_string = name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.id)
        count = User.objects.filter(groups__name=group_string).count()
        if(count < 1):
            problems.append("Manuscript must have at least one author role assigned.")
        return problems
    
    def can_begin(self):
        problems = self.can_begin_return_problems()
        return not problems

    @transition(field=_status, source=Status.NEW, target=Status.AWAITING_INITIAL, conditions=[can_begin],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_CHANGE_M, instance))
    def begin(self):
        pass #Here add any additional actions related to the state change

    #-----------------------

    def can_add_submission(self):
        # Technically we don't need to check 'in_progress' as in that case the manuscript will be processing, but redundancy is ok
        #try:

        if (self.manuscript_submissions.filter(Q(_status=Submission.Status.NEW)| Q(_status=Submission.Status.IN_PROGRESS_EDITION)
                                             | Q(_status=Submission.Status.IN_PROGRESS_CURATION)| Q(_status=Submission.Status.IN_PROGRESS_VERIFICATION)).count() != 0):
            return False
        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.AWAITING_INITIAL, Status.AWAITING_RESUBMISSION], target=RETURN_VALUE(), conditions=[can_add_submission],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance))
    def add_submission_noop(self):
        return self._status

    #-----------------------

    #Conditions: Submission with status of new
    def can_review(self):
        if(self.manuscript_submissions.filter(_status=Submission.Status.NEW).count() != 1):
            return False
        return True

    # Perm: ability to create/edit a submission
    @transition(field=_status, source=[Status.AWAITING_INITIAL, Status.AWAITING_RESUBMISSION], target=Status.REVIEWING, conditions=[can_review],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance))
    def review(self):
        #update submission status here?
        pass #Here add any additional actions related to the state change

    #-----------------------

    #Conditions: Submission with status of new
    #TODO: Add the above? Not sure if its still needed
    def can_process(self):
        return True

    # Perm: ability to create/edit a submission
    @transition(field=_status, source=[Status.REVIEWING], target=Status.PROCESSING, conditions=[can_process],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_APPROVE, instance))
    def process(self):
        #update submission status here?
        pass #Here add any additional actions related to the state change

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.NEW, Status.AWAITING_INITIAL, Status.AWAITING_RESUBMISSION], target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_CHANGE_M,instance))
    def edit_noop(self):
        return self._status

    #-----------------------

    #TODO: Address limitation with having only one manuscript version. If its being edited as part of a resubmission what do we do about viewing?
    #      Do we just allow viewing whatever is there? Do we block it during certain states. Maybe it'll be less of an issue if we can put all versioned data in the submission?
    #
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: (#(instance._status == Status.NEW and user.has_any_perm(c.PERM_MANU_ADD_M,instance.manuscript)) or #add_manuscript means any other editor can see it (even from a different pub...)
                                            (instance._status != instance.Status.NEW and user.has_any_perm(c.PERM_MANU_VIEW_M, instance))) )
    def view_noop(self):
        return self._status

@receiver(post_delete, sender=Manuscript, dispatch_uid='manuscript_delete_groups_signal')
def delete_manuscript_groups(sender, instance, using, **kwargs):
    Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(instance.id)).delete()


####################################################

# Stores info about all the files in git. Needed for tag/description, but also useful to have other info on-hand
# Even thought is code supports parent manuscript, it is not used
class GitFile(AbstractCreateUpdateModel):
    #this is also referenced in Note.ref_file_type
    class FileTag(models.TextChoices):
        CODE = 'code', _('Code')
        DATA = 'data', _('Data')
        DOC_README = 'doc_readme', _('Documentation - Readme')
        DOC_CODEBOOK = 'doc_codebook', _('Documentation - Codebook')
        DOC_OTHER = 'doc_other', _('Documentation - Other')
        UNSET = '-', _('-')

    #git_hash = models.CharField(max_length=40, verbose_name='SHA-1', help_text='SHA-1 hash of a blob or subtree based on its associated mode, type, and filename.') #we don't store this currently
    md5 = models.CharField(max_length=32, verbose_name='md5', help_text='Generated cryptographic hash of the file contents. Used to tell if a file has changed between versions.') #, default="", )
    #We store name and path separately for ease of access and use in dropdowns
    path = models.CharField(max_length=4096, verbose_name='file path', help_text='The path of the folders holding the file, not including the filename')
    name = models.CharField(max_length=4096, verbose_name='file name', help_text='The name of the file')
    date = models.DateTimeField(verbose_name='file creation date')
    size = models.IntegerField(verbose_name='file size', help_text='The size of the file in bytes')
    tag = models.CharField(max_length=14, choices=FileTag.choices, default=FileTag.UNSET, verbose_name='file type') 
    description = models.CharField(max_length=1024, default="", verbose_name='file description')

    #linked = models.BooleanField(default=True)
    parent_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE, related_name='submission_files')
    parent_manuscript = models.ForeignKey(Manuscript, null=True, blank=True, on_delete=models.CASCADE, related_name='manuscript_files')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['path', 'name', 'parent_submission'], name='GitFile submission and path')
        ]
        indexes = [
            models.Index(fields=['path', 'name', 'parent_submission']),
        ]

    @property
    def parent(self):
        if self.parent_submission_id is not None:
            return self.parent_submission
        if self.parent_manuscript_id is not None:
            return self.parent_submission
        raise AssertionError("Neither 'parent_submission' or 'parent_manuscript' is set")

    def save(self, *args, **kwargs):
        parents = 0
        parents += (self.parent_submission_id is not None)
        parents += (self.parent_manuscript_id is not None)
        if(parents > 1):
            raise AssertionError("Multiple parents set")

        if not self.id:
            self.date = timezone.now()

        super(GitFile, self).save(*args, **kwargs)

#Note: If you add required fields here or in the form, you'll need to disable them. See unused_code.py
class Note(AbstractCreateUpdateModel):
    class RefCycle(models.TextChoices):
        SUBMISSION = 'submission', _('Submission')
        EDITION = 'edition', _('Edition')
        CURATION = 'curation', _('Curation')
        VERIFICATION = 'verification', _('Verification')

    text    = models.TextField(default="", blank=True, verbose_name='Note Text')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    note_replied_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='note_responses')

    parent_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    #TODO: Eventually delete all these other parent options if we end up never using them.
    parent_edition = models.ForeignKey(Edition, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    parent_curation = models.ForeignKey(Curation, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    parent_verification = models.ForeignKey(Verification, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    #parent_file = models.ForeignKey(GitFile, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')

    #note this is not a "parent" relationship like above
    manuscript = models.ForeignKey(Manuscript, on_delete=models.CASCADE)

    #Instead of being parents, these refer to which file or category of the submission a note refers to.
    #The idea is that we want to show all these notes on the submission page, but then give the ability to specify what part of the submission they are related to
    ref_file = models.ForeignKey(GitFile, null=True, blank=True, on_delete=models.CASCADE, related_name='ref_notes')
    ref_file_type = models.CharField(max_length=14, choices=GitFile.FileTag.choices, blank=True, verbose_name='file type') 
    
    #Instead of having notes attached to edition/curation/verification, we have all notes on submission but track when during the process the note was made.
    #We could have inferred this from the author, but that really stinks for testing as an admin (who can have multiple roles)
    ref_cycle = models.CharField(max_length=12, choices=RefCycle.choices) 

    @property
    def parent(self):
        if self.parent_submission_id is not None:
            return self.parent_submission
        if self.parent_edition_id is not None:
            return self.parent_edition
        if self.parent_curation_id is not None:
            return self.parent_curation
        if self.parent_verification_id is not None:
            return self.parent_verification
        # if self.parent_file_id is not None:
        #     return self.parent_file
        raise AssertionError("Neither 'parent_submission', 'parent_edition', 'parent_curation' or 'parent_verification' is set")
    
    def save(self, *args, **kwargs):
        parents = 0
        parents += (self.parent_submission_id is not None)
        parents += (self.parent_edition_id is not None)
        parents += (self.parent_curation_id is not None)
        parents += (self.parent_verification_id is not None)
        # parents += (self.parent_file_id is not None)
        if(parents > 1):
            raise AssertionError("Multiple parents set")

        print(self.text)
        refs = 0
        refs += (self.ref_file is not None)
        print(self.ref_file)
        refs += (self.ref_file_type is not '')
        print(self.ref_file_type)
        if(refs > 1):
            raise AssertionError("Multiple References set")

        first_save = False
        if not self.pk:
            first_save = True
            if(self.manuscript_id is None):
                if self.parent_submission_id is not None:
                    self.manuscript = self.parent_submission.manuscript
                # elif self.parent_file_id is not None:
                #     self.manuscript = self.parent_file.parent_submission.manuscript
                else:
                    self.manuscript = self.parent.submission.manuscript

                #set note ref cycle
                if self.parent_submission_id is not None:
                    if not hasattr(self.parent_submission, 'submission_edition'): #if not self.parent_submission.submission_edition:
                        self.ref_cycle = self.RefCycle.SUBMISSION
                    elif not hasattr(self.parent_submission, 'submission_curation'): #elif not self.parent_submission.submission_curation:
                        self.ref_cycle = self.RefCycle.EDITION
                    elif not hasattr(self.parent_submission, 'submission_verification'): #elif not self.parent_submission.submission_verification:
                        self.ref_cycle = self.RefCycle.CURATION
                    else:
                        self.ref_cycle = self.RefCycle.VERIFICATION

        super(Note, self).save(*args, **kwargs)
        if first_save and local.user != None and local.user.is_authenticated: #maybe redundant
            assign_perm(c.PERM_NOTE_VIEW_N, local.user, self) 
            assign_perm(c.PERM_NOTE_CHANGE_N, local.user, self) 
            assign_perm(c.PERM_NOTE_DELETE_N, local.user, self) 

    #TODO: If implementing fsm can_edit, base it upon the creator of the note

#TODO: Package and software seem extremely similar, maybe we don't need both
class VerificationMetadataPackage(models.Model):
    name = models.CharField(max_length=200, blank=True, default="", verbose_name='Name')
    version = models.CharField(max_length=200, blank=True, default="", verbose_name='Version')
    source_default_repo = models.BooleanField(default=False, blank=True, verbose_name='Source - Default Repository')
    source_cran = models.BooleanField(default=False, blank=True, verbose_name='Source - CRAN')
    source_author_website = models.BooleanField(default=False, blank=True, verbose_name='Source - Author Website')
    source_dataverse = models.BooleanField(default=False, blank=True, verbose_name='Source - Dataverse Archive')
    source_other = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Source - Other')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_packages")

class VerificationMetadataSoftware(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    code_repo_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Code Repository URL')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_softwares")

class VerificationMetadataBadge(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    badge_type = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Type')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    definition_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Definition URL')
    logo_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Logo URL')
    issuing_org = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Issuing Organization')
    issuing_date = models.DateField(blank=True, null=True, verbose_name='Issuing Date')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_badges")

class VerificationMetadataAudit(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='URL')
    organization = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Organization')
    verified_results = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Verified Results')
    exceptions = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Exceptions')
    exception_reason = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Exception Reason')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_audits")

class VerificationMetadata(AbstractCreateUpdateModel):
    operating_system = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Operating System')
    machine_type = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Machine Type')
    scheduler = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Scheduler Module')
    platform = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Platform')
    processor_reqs = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Processor Requirements')
    host_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Hosting Institution URL')
    memory_reqs = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Memory Reqirements')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name="submission_vmetadata")

############### POST-SAVE ################

# post-save signal to update history with list of fields changed
@receiver(post_save, sender=Manuscript, dispatch_uid="add_history_info_manuscript")
@receiver(post_save, sender=User, dispatch_uid="add_history_info_user")
@receiver(post_save, sender=Submission, dispatch_uid="add_history_info_submission")
@receiver(post_save, sender=Curation, dispatch_uid="add_history_info_curation")
@receiver(post_save, sender=Verification, dispatch_uid="add_history_info_verification")
@receiver(post_save, sender=Note, dispatch_uid="add_history_info_note")
def add_history_info(sender, instance, **kwargs):
    try:
        new_record, old_record = instance.history.order_by('-history_date')[:2]
        delta = new_record.diff_against(old_record)
        new_record.history_change_list = str(delta.changed_fields)
        new_record.save()
    except ValueError:
        pass #On new object creation there are not 2 records to do a history diff on.
