import logging
import uuid
# from . import constants as c
from django.conf import settings
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
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models.signals import post_delete
from guardian.shortcuts import get_users_with_perms, assign_perm
from simple_history.models import HistoricalRecords
from simple_history.utils import update_change_reason
from corere.main import constants as c
from corere.main import git as g
from corere.main import docker as d
from corere.main import wholetale_corere as w
from corere.apps.wholetale import models as wtm
from corere.main.middleware import local
from corere.main.utils import fsm_check_transition_perm
from django.contrib.postgres.fields import ArrayField
#from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_group, get_perms
from autoslug import AutoSlugField
from datetime import date, datetime
from django.db.models.signals import m2m_changed

#for custom invitation class
from invitations import signals
from invitations.models import Invitation
from invitations.adapters import get_invitations_adapter
from django.utils.crypto import get_random_string
from django.contrib.sites.models import Site
from django.urls import reverse


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

    #invite_key = models.CharField(max_length=64, blank=True)
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    email = models.EmailField(unique=True, blank=False)
    wt_id = models.CharField(max_length=24, blank=True, null=True, verbose_name='User ID in Whole Tale')

    #This parameter is to track the last time a user has been sent manually by corere to oauthproxy's sign_in page
    #It is not an exact parameter because a user could potentially alter their url string to have it not be set right
    #But that is ok because the only reprocussion is they may get shown an oauthproxy login inside their iframe
    last_oauthproxy_forced_signin = models.DateTimeField(default=datetime(1900, 1, 1))

    # Django Guardian has_perm does not check whether the user has a global perm.
    # We always want that in our project, so this function checks both
    # See for more info: https://github.com/django/django/pull/9581
    def has_any_perm(self, perm_string, obj):
        return self.has_perm(c.perm_path(perm_string)) or self.has_perm(perm_string, obj)

    def save(self, *args, **kwargs):
        if settings.CONTAINER_DRIVER == "wholetale" and self.pk is not None:
            orig = User.objects.get(pk=self.pk)
            if orig.is_superuser != self.is_superuser: #If change in superuser status
                admin_wtm_group = wtm.GroupConnector.objects.get(is_admins=True)
                wtc = w.WholeTaleCorere(admin=True)
                if self.is_superuser:
                    wtc.invite_user_to_group(self.wt_id , admin_wtm_group.wt_id)
                else:
                    wtc.remove_user_from_group(self.wt_id , admin_wtm_group.wt_id)

        super(User, self).save(*args, **kwargs)

####################################################

class Edition(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = 'new', '---'
        ISSUES = 'issues', 'Issues'
        NO_ISSUES = 'no_issues', 'No Issues'

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Review', help_text='Was the submission approved by the editor')
    report = models.TextField(default="", verbose_name='Details')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_edition')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_edition")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(not self.pk and self.submission._status != Submission.Status.IN_PROGRESS_EDITION):
                raise FieldError('A edition cannot be added to a submission unless its status is: ' + Submission.Status.IN_PROGRESS_EDITION)
        except Edition.submission.RelatedObject:
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
        NEW = 'new', '---'
        INCOM_MATERIALS = 'incom_materials', 'Incomplete Materials'
        MAJOR_ISSUES = 'major_issues', 'Major Issues'
        MINOR_ISSUES = 'minor_issues', 'Minor Issues'
        NO_ISSUES = 'no_issues', 'No Issues'

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Review', help_text='Was the submission approved by the curator')
    report = models.TextField(default="", verbose_name='Details')
    needs_verification = models.BooleanField(default=False, verbose_name="Needs Verification")
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_curation')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_curation")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(not self.pk and self.submission._status != Submission.Status.IN_PROGRESS_CURATION):
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
        NEW = 'new', '---'
        NOT_ATTEMPTED = 'not_attempted', 'Not Attempted'
        MINOR_ISSUES = 'minor_issues', 'Minor Issues'
        MAJOR_ISSUES = 'major_issues', 'Major Issues'
        SUCCESS_W_MOD = 'success_w_mod', 'Success with Modification'
        SUCCESS = 'success', 'Success'

    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Review', help_text='Was the submission able to be verified')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_verification')
    report = models.TextField(default="", verbose_name='Details')
    code_executability = models.CharField(max_length=2000, default="", verbose_name='Code Executability')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_verification")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(not self.pk and self.submission._status != Submission.Status.IN_PROGRESS_VERIFICATION):
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
        REJECTED_EDITOR = 'rejected_editor'
        IN_PROGRESS_CURATION = 'in_progress_curation'
        IN_PROGRESS_VERIFICATION = 'in_progress_verification'
        REVIEWED_AWAITING_REPORT = 'reviewed_awaiting_report'
        REVIEWED_REPORT_AWAITING_APPROVAL = 'reviewed_awaiting_approve'
        RETURNED = 'returned'

    _status = FSMField(max_length=25, choices=Status.choices, default=Status.NEW, verbose_name='Submission review status', help_text='The status of the submission in the review process')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_submissions")
    version_id = models.IntegerField(verbose_name='Version number')
    files_changed = models.BooleanField(default=True)
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

    high_performance = models.BooleanField(default=False, verbose_name='Does this submission require a high-performance compute environment?')
    contents_gis = models.BooleanField(default=False, verbose_name='Does this submission contain GIS data and mapping?')
    contents_proprietary = models.BooleanField(default=False, verbose_name='Does this submission contain restricted or proprietary data?')
    contents_proprietary_sharing = models.BooleanField(default=False, verbose_name='Are you restricted from sharing this data with Odum for verification only?')
    
    launch_issues = models.TextField(max_length=1024, blank=True, null=True, default="", verbose_name='Container Launch Issues', help_text='Issues faced when attempting to launch the container')
    
    class Meta:
        default_permissions = ()
        ordering = ['version_id']
        unique_together = ('manuscript', 'version_id',)

    def save(self, *args, **kwargs):
        prev_max_version_id = self.manuscript.get_max_submission_version_id()
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
        
        girderToken = kwargs.pop('girderToken', None)
        super(Submission, self).save(*args, **kwargs)

        if(first_save):
            if self.manuscript.compute_env != 'Other' and settings.CONTAINER_DRIVER == "wholetale":
                wtc = w.WholeTaleCorere(admin=True)
                tale = self.manuscript.manuscript_tales.get(original_tale=None)
                group = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id))
                wtc.set_group_access(tale.wt_id, wtc.AccessType.WRITE, group.wholetale_group)
                tale.submission = self #update the submission for the root tale
                tale.save()

            if(self.version_id > 1):
                prev_submission = Submission.objects.get(manuscript=self.manuscript, version_id=prev_max_version_id)
                for gfile in prev_submission.submission_files.all():
                    new_gfile = gfile
                    new_gfile.parent_submission = self
                    new_gfile.id = None
                    new_gfile.save()
                if self.manuscript.compute_env != 'Other' and settings.CONTAINER_DRIVER == "wholetale":
                    for tc in tale.tale_copies.all(): #delete copy instances from previous submission. Note this happens as admin from the previous connection above
                        wtc.delete_tale(tale.wt_id) #deletes instances as well
        elif self._status == self.Status.REJECTED_EDITOR and self.manuscript.compute_env != 'Other' and settings.CONTAINER_DRIVER == "wholetale": #If editor rejects we need to give the author write access again to the same submission
            wtc = w.WholeTaleCorere(admin=True)
            tale = self.manuscript.manuscript_tales.get(original_tale=None)
            group = Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id))
            wtc.set_group_access(tale.wt_id, wtc.AccessType.WRITE, group.wholetale_group)
            tale.submission = self #update the submission for the root tale
            tale.save()

    ##### Queries #####

    def get_public_curator_notes_general(self):
        return self._get_public_general_notes_by_refcycle(Note.RefCycle.CURATION)

    def get_public_verifier_notes_general(self):
        return self._get_public_general_notes_by_refcycle(Note.RefCycle.VERIFICATION)

    def get_public_curator_notes_category(self):
        return self._get_public_category_notes_by_refcycle(Note.RefCycle.CURATION)

    def get_public_verifier_notes_category(self):
        return self._get_public_category_notes_by_refcycle(Note.RefCycle.VERIFICATION)

    def get_public_curator_notes_file(self):
        return self._get_public_file_notes_by_refcycle(Note.RefCycle.CURATION)

    def get_public_verifier_notes_file(self):
        return self._get_public_file_notes_by_refcycle(Note.RefCycle.VERIFICATION)

    def _get_public_general_notes_by_refcycle(self, refcycle):
        queryset = Note.objects.filter(parent_submission=self, ref_cycle=refcycle, ref_file=None, ref_file_type='').order_by('created_at')
        return self._get_public_notes_by_ref_cycle(queryset)

    def _get_public_category_notes_by_refcycle(self, refcycle):
        queryset = Note.objects.filter(~Q(ref_file_type=''), parent_submission=self, ref_cycle=refcycle).order_by('ref_file_type', 'created_at')
        return self._get_public_notes_by_ref_cycle(queryset)

    def _get_public_file_notes_by_refcycle(self, refcycle):
        #queryset = Note.objects.filter(parent_submission=self, ref_cycle=refcycle, ref_file_type='').order_by('-created_at')
        queryset = Note.objects.filter(~Q(ref_file=None), parent_submission=self, ref_cycle=refcycle).order_by('ref_file__name','created_at')
        return self._get_public_notes_by_ref_cycle(queryset)

    #We check an author is public by checking if the author group can view. This is based on the assumption that we always assign editor the same view permissions as author.
    def _get_public_notes_by_ref_cycle(self, queryset):
        public_notes = []
        for note in queryset:
            note_perms = get_perms(Group.objects.get(name=c.GROUP_ROLE_AUTHOR), note)
            if 'view_note' in note_perms:
                public_notes.append(note)
        return public_notes

    def get_gitfiles_pathname(self, combine=False):
        values_list = GitFile.objects.values('path','name').filter(parent_submission=self)        
        if(combine):
            combine_list = []
            for v in values_list:
                combine_list.append(v.get('path')+v.get('name'))
            return combine_list
        else:
            return values_list

    ##### django-fsm (workflow) related functions #####

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[Status.NEW, Status.REJECTED_EDITOR], target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: (( (instance._status == instance.Status.NEW or instance._status == instance.Status.REJECTED_EDITOR) and user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript))
                                            or (instance._status != instance.Status.NEW and instance._status != instance.Status.REJECTED_EDITOR and user.has_any_perm(c.PERM_MANU_VIEW_M, instance.manuscript))) )
    def view_noop(self):
        return self._status

    #-----------------------

    def can_submit(self):
        return True

    #TODO: I'm not sure if on_error is ever hit, but we'd want it to be NEW or REJECTED_EDITOR conditionally.
    @transition(field=_status, source=[Status.NEW, Status.REJECTED_EDITOR], target=RETURN_VALUE(), on_error=Status.NEW, conditions=[can_submit],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance.manuscript)) #MAD: Used same perm as add, do we want that?
    def submit(self, user):
        if has_transition_perm(self.manuscript.review, user): #checking here because we need the user
            self.manuscript.review()
            self.manuscript.save()
            if self.manuscript.skip_edition:
                return self.Status.IN_PROGRESS_CURATION
            else:
                return self.Status.IN_PROGRESS_EDITION
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
            if(self.submission_curation.needs_verification == False):
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
        if(self.submission_edition._status == Edition.Status.NO_ISSUES):
            self.manuscript.process()
            self.manuscript.save()
            return self.Status.IN_PROGRESS_CURATION
        else:
            #g.create_submission_branch(self) #We create the submission branch before returning the submission, to "save" the current state of the repo for history
            self.manuscript._status = Manuscript.Status.AWAITING_RESUBMISSION
            self.manuscript.save()
            return self.Status.REJECTED_EDITOR

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
            if(self.submission_curation.needs_verification == True):
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
    
    def can_send_report(self):
        return True

    @transition(field=_status, source=Status.REVIEWED_AWAITING_REPORT, target=Status.REVIEWED_REPORT_AWAITING_APPROVAL, conditions=[can_send_report],
            permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_CURATE, instance.manuscript)))
    def send_report(self):
        pass

    #-----------------------
    
    #TODO: It would be better to have this logic as a manuscript transition. 
    # Its somewhat annoying to get to the latest submission from the manuscript, so for now it'll remain here.
    def can_finish_submission(self):
        return True

    @transition(field=_status, source=Status.REVIEWED_REPORT_AWAITING_APPROVAL, target=Status.RETURNED, conditions=[can_finish_submission],
            permission=lambda instance, user: ( user.has_any_perm(c.PERM_MANU_APPROVE, instance.manuscript)))
    def finish_submission(self):
        if(self.submission_curation._status == Curation.Status.NO_ISSUES):
            if(self.submission_curation.needs_verification == False or (self.submission_curation.needs_verification == True and self.submission_verification._status == Verification.Status.SUCCESS)):
                self.manuscript._status = Manuscript.Status.COMPLETED
                ## We decided to leave completed manuscripts in the list and toggle their visibility

                # Rename existing groups (add completed suffix) when done for clean-up and reporting
                author_name = name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)
                author_group = Group.objects.get(name=author_name)
                author_group.name = author_name + " " + c.GROUP_COMPLETED_SUFFIX
                author_group.save()

                editor_name = name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)
                editor_group = Group.objects.get(name=editor_name)
                editor_group.name = editor_name + " " + c.GROUP_COMPLETED_SUFFIX
                editor_group.save()

                curator_name = name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)
                curator_group = Group.objects.get(name=curator_name)
                curator_group.name = curator_name + " " + c.GROUP_COMPLETED_SUFFIX
                curator_group.save()

                verifier_name = name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)
                verifier_group = Group.objects.get(name=verifier_name)
                verifier_group.name = verifier_name + " " + c.GROUP_COMPLETED_SUFFIX
                verifier_group.save()

                self.manuscript.save()
                return
            
        self.manuscript._status = Manuscript.Status.AWAITING_RESUBMISSION
        self.manuscript.save()
        return

####################################################

class Author(models.Model):
    class IdScheme(models.TextChoices):
        ORCID = 'ORCID', 'ORCID'
        ISNI = 'ISNI', 'ISNI'
        LCNA = 'LCNA', 'LCNA'
        VIAF = 'VIAF', 'VIAF'
        GND = 'GND', 'GND'
        DAI = 'DAI', 'DAI'
        REID = 'ResearcherID', 'ResearcherID'
        SCID = 'ScopusID', 'ScopusID'

    first_name = models.CharField(max_length=150, blank=False, null=False,  verbose_name='First Name')
    last_name =  models.CharField(max_length=150, blank=False, null=False,  verbose_name='Last Name')
    identifier_scheme = models.CharField(max_length=14, blank=True, null=True,  choices=IdScheme.choices, verbose_name='Identifier Scheme') 
    identifier = models.CharField(max_length=150, blank=True, null=True, verbose_name='Identifier')
    # position = models.IntegerField(verbose_name='Position', help_text='Position/order of the author in the list of authors')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_authors")

class DataSource(models.Model):
    text = models.CharField(max_length=4000, blank=False, null=False, default="", verbose_name='Data Source')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_data_sources")

class Keyword(models.Model):
    text = models.CharField(max_length=200, blank=False, null=False, default="", verbose_name='Keyword')
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_keywords")

####################################################

class Manuscript(AbstractCreateUpdateModel):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        AWAITING_INITIAL = 'awaiting_init', 'Awaiting Initial Submission'
        AWAITING_RESUBMISSION = 'awaiting_resub', 'Awaiting Author Resubmission'
        REVIEWING = 'reviewing', 'Editor Reviewing'
        PROCESSING = 'processing', 'Processing Submission'
        COMPLETED = 'completed', 'Completed'

    class Subjects(models.TextChoices):
        AGRICULTURAL = 'agricultural', 'Agricultural Sciences'
        ARTS_AND_HUMANITIES = 'arts', 'Arts and Humanities'
        ASTRONOMY_ASTROPHYSICS = 'astronomy', 'Astronomy and Astrophysics'
        BUSINESS_MANAGEMENT = 'business', 'Business and Management'
        CHEMISTRY = 'chemistry', 'Chemistry'
        COMPUTER_INFORMATION = 'computer', 'Computer and Information Science'
        ENVIRONMENTAL = 'environmental', 'Earth and Environmental Sciences'
        ENGINEERING = 'engineering', 'Engineering'
        LAW = 'law', 'Law'
        MATHEMATICS = 'mathematics', 'Mathematical Sciences'
        HEALTH = 'health', 'Medicine, Health and Life Sciences'
        PHYSICS = 'physics', 'Physics'
        SOCIAL = 'social', 'Social Sciences'
        OTHER = 'other', 'Other'

    pub_name = models.CharField(max_length=200, default="", verbose_name='Manuscript Title', help_text='Title of the manuscript')
    pub_id = models.CharField(max_length=200, default="", db_index=True, verbose_name='Manuscript #', help_text='The internal ID from the publication')
    qual_analysis = models.BooleanField(default=False, blank=True, null=True, verbose_name='Qualitative Analysis', help_text='Whether this manuscript includes qualitative analysis')
    qdr_review = models.BooleanField(default=False, blank=True, null=True, verbose_name='QDR Review', help_text='Does this manuscript need verification of qualitative results by QDR?')
    contact_first_name = models.CharField(max_length=150, verbose_name='Corresponding Author Given Name', help_text='Given name of the publication contact that will be stored in Dataverse')
    contact_last_name =  models.CharField(max_length=150, verbose_name='Corresponding Author Surname', help_text='Surname of the publication contact that will be stored in Dataverse')
    contact_email = models.EmailField(null=True, verbose_name='Corresponding Author Email Address', help_text='Email address of the publication contact that will be stored in Dataverse')
    dataverse_doi = models.CharField(max_length=150, blank=True, verbose_name='Dataverse DOI', help_text='DOI of the publication in Dataverse')
    description = models.TextField(max_length=1024, blank=True, null=True, default="", verbose_name='Abstract', help_text='The abstract for the manuscript')
    subject = models.CharField(max_length=14, blank=True, null=True, choices=Subjects.choices, verbose_name='Subject') 
    additional_info = models.TextField(max_length=1024, blank=True, null=True, default="", verbose_name='Additional Info', help_text='Additional info about the manuscript (e.g., approved exemptions, restricted data, etc).')
    # producer_first_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Producer First Name')
    # producer_last_name =  models.CharField(max_length=150, blank=True, null=True, verbose_name='Producer Last Name')
    _status = FSMField(max_length=15, choices=Status.choices, default=Status.NEW, verbose_name='Manuscript Status', help_text='The overall status of the manuscript in the review process')
    #TODO: When fixing local container mode (non settings.CONTAINER_DRIVER == 'wholetale'), we will need to generate a list of compute environments to populate the form for selecting the below fields
    compute_env = models.CharField(max_length=100, blank=True, null=True, verbose_name='Compute Environment Format') #This is set to longer than 24 to bypass a validation check due to form weirdness. See the manuscript form save function for more info
    compute_env_other = models.TextField(max_length=1024, blank=True, null=True, default="", verbose_name='Other Environment Details', help_text='Details about the unlisted environment')
    skip_edition = models.BooleanField(default=False, help_text='Is this manuscript being run without external Authors or Editors')

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) #currently only used for naming a file folder on upload. Needed as id doesn't exist until after create
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,], excluded_fields=['slug'])
    slug = AutoSlugField(populate_from='get_display_name') #TODO: make this based off other things?

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

    #There are 3 types of groups in this code. Django groups, Whole Tale groups stored in Whole Tale, and wholetale app groups connecting the two and storing the info locally
    def save(self, *args, **kwargs):
        first_save = False
        if not self.pk:
            first_save = True
            if settings.SKIP_EDITION: #Set here because we want it to save with super
                self.skip_edition = True

        if not first_save and settings.CONTAINER_DRIVER == "wholetale":
            orig = Manuscript.objects.get(pk=self.pk)
            if orig.compute_env != self.compute_env:
                old_tales = self.manuscript_tales.all()
                # print(old_tales)
                wtc = w.WholeTaleCorere(admin=True)
                for ot in old_tales:
                    wtc.delete_tale(ot.wt_id)
                self.manuscript_tales.all().delete()

        super(Manuscript, self).save(*args, **kwargs)

        if first_save:
            # Note these works alongside global permissions defined in signals.py
            # TODO: Make this concatenation standardized
            editor_group_name = c.generate_group_name(c.GROUP_MANUSCRIPT_EDITOR_PREFIX, self)
            group_manuscript_editor, created = Group.objects.get_or_create(name=editor_group_name)
            assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_DELETE_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_ADD_AUTHORS, group_manuscript_editor, self) 
            assign_perm(c.PERM_MANU_APPROVE, group_manuscript_editor, self)

            author_group_name = c.generate_group_name(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX, self)
            group_manuscript_author, created = Group.objects.get_or_create(name=author_group_name)
            assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_author, self)
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_author, self) 
            #assign_perm(c.PERM_MANU_ADD_AUTHORS, group_manuscript_author, self) 
            assign_perm(c.PERM_MANU_ADD_SUBMISSION, group_manuscript_author, self) 

            curator_group_name = c.generate_group_name(c.GROUP_MANUSCRIPT_CURATOR_PREFIX, self)
            group_manuscript_curator, created = Group.objects.get_or_create(name=curator_group_name)
            assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_curator, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_curator, self) 
            assign_perm(c.PERM_MANU_CURATE, group_manuscript_curator, self) 

            verifier_group_name = c.generate_group_name(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX, self)
            group_manuscript_verifier, created = Group.objects.get_or_create(name=verifier_group_name)
            #assign_perm(c.PERM_MANU_CHANGE_M, group_manuscript_verifier, self) 
            assign_perm(c.PERM_MANU_VIEW_M, group_manuscript_verifier, self) 
            assign_perm(c.PERM_MANU_VERIFY, group_manuscript_verifier, self) 

            g.create_manuscript_repo(self)
            g.create_submission_repo(self)

            if settings.CONTAINER_DRIVER == "wholetale": #NOTE: We don't check compute_env != 'Other' here because we don't know it yet. It means we create groups for manuscripts that won't be in wholetale but that's ok
                #Create 4 WT groups for the soon to be created tale (after we get the author info). Also the wtm.GroupConnectors that connect corere groups and WT groups
                wtc = w.WholeTaleCorere(admin=True)
                wtc_group_editor = wtc.create_group_with_hash(editor_group_name)
                wtm_group_editor = wtm.GroupConnector.objects.create(corere_group=group_manuscript_editor, wt_id=wtc_group_editor['_id'], manuscript=self)
                wtc_group_author = wtc.create_group_with_hash(author_group_name)
                wtm_group_author = wtm.GroupConnector.objects.create(corere_group=group_manuscript_author, wt_id=wtc_group_author['_id'], manuscript=self)
                wtc_group_curator = wtc.create_group_with_hash(curator_group_name)
                wtm_group_curator = wtm.GroupConnector.objects.create(corere_group=group_manuscript_curator, wt_id=wtc_group_curator['_id'], manuscript=self)
                wtc_group_verifier = wtc.create_group_with_hash(verifier_group_name)
                wtm_group_verifier = wtm.GroupConnector.objects.create(corere_group=group_manuscript_verifier, wt_id=wtc_group_verifier['_id'], manuscript=self)
                
            group_manuscript_editor.user_set.add(local.user) #TODO: Should be dynamic on role or more secure, but right now only editors create manuscripts. Will need to fix wt invite below as well.
        
        if settings.CONTAINER_DRIVER == "wholetale" and self.compute_env and self.compute_env != 'Other' and not self.manuscript_tales.all().exists():
            #We create our root tale for the manuscript after the compute env has been provided. This triggers before there were ever tales, and after tales were deleted due to compute_env switch.
            wtm_group_editor = Group.objects.get(name=c.generate_group_name(c.GROUP_MANUSCRIPT_EDITOR_PREFIX, self)).wholetale_group
            wtm_group_author = Group.objects.get(name=c.generate_group_name(c.GROUP_MANUSCRIPT_AUTHOR_PREFIX, self)).wholetale_group
            wtm_group_curator = Group.objects.get(name=c.generate_group_name(c.GROUP_MANUSCRIPT_CURATOR_PREFIX, self)).wholetale_group
            wtm_group_verifier = Group.objects.get(name=c.generate_group_name(c.GROUP_MANUSCRIPT_VERIFIER_PREFIX, self)).wholetale_group
            
            wtc = w.WholeTaleCorere(admin=True)
            tale_title = f"{self.get_display_name()} - {self.id}"

            wtc_tale = wtc.create_tale(tale_title, self.compute_env)
            tale = wtm.Tale()
            tale.manuscript = self
            tale.wt_id = wtc_tale["_id"]
            tale.group_connector = wtm_group_author
            tale.save()

            wtc.set_group_access(tale.wt_id, wtc.AccessType.READ, wtm_group_editor)
            wtc.set_group_access(tale.wt_id, wtc.AccessType.READ, wtm_group_author)
            wtc.set_group_access(tale.wt_id, wtc.AccessType.READ, wtm_group_curator)
            wtc.set_group_access(tale.wt_id, wtc.AccessType.READ, wtm_group_verifier)

            if not first_save:
                try: #All this code is for recreating a tale after an environment switch
                    latest_sub = self.get_latest_submission()
                    tale.submission = latest_sub
                    tale.save()
                    wtc.upload_files(tale.wt_id, g.get_submission_repo_path(self)) #Upload existing files. Only should actually do anything when changing compute_env. This could take a long time, we don't do anything about that right now.
                    if latest_sub._status == Submission.Status.NEW or latest_sub._status == Submission.Status.REJECTED_EDITOR:
                        wtc.set_group_access(tale.wt_id, wtc.AccessType.WRITE, wtm_group_author)
                except Submission.DoesNotExist:
                    pass

            #TODO: we need to set the tale access for the root tale for the author based upon the group
                
            #TODO-WT: We aren't handling the case where a compute env is changed and then a user attempts to run a compute env for a previous submission with a different env.
            #         I think my best bet is to make a custom error for this? "The environment type for this manuscript has changed. You cannot run submissions from before this change took place."

    def is_complete(self):
        return self._status == Manuscript.Status.COMPLETED

    def get_max_submission_version_id(self):
        return Submission.objects.filter(manuscript=self).aggregate(Max('version_id'))['version_id__max']

    def get_latest_submission(self):
        return Submission.objects.get(manuscript=self, version_id=self.get_max_submission_version_id())

    def get_landing_url(self):
        return settings.CONTAINER_PROTOCOL + "://" + settings.SERVER_ADDRESS + "/manuscript/" + str(self.id)

    def get_display_name(self):
        try:
            return self.pub_id + " (" + self.contact_last_name + ")"
        except TypeError:
            return self.pub_name

    def get_gitfiles_pathname(self, combine=False):
        values_list = GitFile.objects.values('path','name').filter(parent_manuscript=self) 
        if(combine):
            combine_list = []
            for v in values_list:
                combine_list.append(v.get('path')+v.get('name'))
            return combine_list
        else:
            return values_list

    # def __str__(self):
    #     return '{0}: {1}'.format(self.id, self.title)

    ##### django-fsm (workflow) related functions #####
    
    #Extra function defined so fsm errors can be passed to use when submitting a form.
    #Conditions: Authors needed, files uploaded [NOT ADDED YET]
    #Note: Right now we enforce the files through a UI check as part of the flow. We don't check it again at the end when begin is called.
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

        if (self.manuscript_submissions.filter(Q(_status=Submission.Status.NEW)| Q(_status=Submission.Status.REJECTED_EDITOR)| Q(_status=Submission.Status.IN_PROGRESS_EDITION)
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
        #technically this'll return true when somehow a submission exists with NEW and another with REJECTED_EDITOR. Should never happen though.
        if(self.manuscript_submissions.filter(_status=Submission.Status.NEW).count() != 1):
            if(self.manuscript_submissions.filter(_status=Submission.Status.REJECTED_EDITOR).count() != 1):
                return False
        return True

    # Perm: ability to create/edit a submission
    @transition(field=_status, source=[Status.AWAITING_INITIAL, Status.AWAITING_RESUBMISSION], target=RETURN_VALUE(), conditions=[can_review],
                permission=lambda instance, user: user.has_any_perm(c.PERM_MANU_ADD_SUBMISSION, instance))
    def review(self):
        if self.skip_edition:
            return self.Status.PROCESSING
        else:
            return self.Status.REVIEWING

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
    Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(instance.id)).delete()
    Group.objects.get(name__startswith=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(instance.id)).delete()

#Class related to locally hosted docker containers
class LocalContainerInfo(models.Model):
    repo_image_name = models.CharField(max_length=128, blank=True, null=True)
    proxy_image_name = models.CharField(max_length=128, blank=True, null=True)
    repo_container_id = models.CharField(max_length=64, blank=True, null=True)
    repo_container_ip = models.CharField(max_length=24, blank=True, null=True)
    # repo_container_port = models.CharField(max_length=5, blank=True, null=True, unique=True) #should be an int?
    proxy_container_id = models.CharField(max_length=64, blank=True, null=True)
    proxy_container_address = models.CharField(max_length=24, blank=True, null=True)
    proxy_container_port = models.IntegerField(blank=True, null=True, unique=True)
    network_ip_substring = models.CharField(max_length=12, blank=True, null=True)
    network_id = models.CharField(max_length=64, blank=True, null=True)
    submission_version = models.IntegerField(blank=True, null=True) #Why didn't I just use submission???
    manuscript = models.OneToOneField('Manuscript', on_delete=models.CASCADE, related_name="manuscript_localcontainerinfo")
    build_in_progress = models.BooleanField(default=False)

    def container_public_address(self):
        #We add 20 because our web server will provide ssl and will be listening on the ports 20 up. But we also change the range of the internal ports
        if(settings.CONTAINER_PROTOCOL == 'https'):
            proxy_container_external_port = self.proxy_container_port + 20
        else:
            proxy_container_external_port = self.proxy_container_port

        return settings.CONTAINER_PROTOCOL + "://" + self.proxy_container_address + ":" + str(proxy_container_external_port) #I don't understand why python decides my charfield is an int?

    def container_network_name(self):
        return "notebook-" + str(self.manuscript.id)

    # def proxy_image_name(self):
    #     return ("oauthproxy-" + str(self.manuscript.id) + "-" + self.manuscript.slug)[:128] + ":" + settings.DOCKER_GEN_TAG

####################################################

# Stores info about all the files in git, as well as metadata about the files
class GitFile(AbstractCreateUpdateModel):
    #this is also referenced in Note.ref_file_type
    class FileTag(models.TextChoices):
        CODE = 'code', 'Code'
        DATA = 'data', 'Data'
        DOC_README = 'doc_readme', 'Documentation - Readme'
        DOC_CODEBOOK = 'doc_codebook', 'Documentation - Codebook'
        DOC_OTHER = 'doc_other', 'Documentation - Other'
        #UNSET = '-','-'

    #git_hash = models.CharField(max_length=40, verbose_name='SHA-1', help_text='SHA-1 hash of a blob or subtree based on its associated mode, type, and filename.') #we don't store this currently
    md5 = models.CharField(max_length=32, verbose_name='md5', help_text='Generated cryptographic hash of the file contents. Used to tell if a file has changed between versions.') #, default="", )
    #We store name and path separately for ease of access and use in dropdowns
    path = models.CharField(max_length=4096, verbose_name='file path', help_text='The path of the folders holding the file, not including the filename')
    name = models.CharField(max_length=4096, verbose_name='file name', help_text='The name of the file')
    date = models.DateTimeField(verbose_name='file creation date')
    size = models.IntegerField(verbose_name='file size', help_text='The size of the file in bytes')
    tag = models.CharField(max_length=14, null=True, blank=True, choices=FileTag.choices, verbose_name='file type')
    description = models.CharField(max_length=1024, null=True, blank=True, default="", verbose_name='file description')

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
        if self.parent_submission_id != None:
            return self.parent_submission
        if self.parent_manuscript_id != None:
            return self.parent_submission
        raise AssertionError("Neither 'parent_submission' or 'parent_manuscript' is set")

    @property
    def full_path(self):
        return self.path + self.name

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
        SUBMISSION = 'submission', 'Submission'
        EDITION = 'edition', 'Edition'
        CURATION = 'curation', 'Curation'
        VERIFICATION = 'verification', 'Verification'

    text    = models.TextField(verbose_name='Note Text')
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])
    note_replied_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='note_responses')
    parent_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')

    #note this is not a "parent" relationship like above
    manuscript = models.ForeignKey(Manuscript, on_delete=models.CASCADE)

    #Instead of being parents, these refer to which file or category of the submission a note refers to.
    #The idea is that we want to show all these notes on the submission page, but then give the ability to specify what part of the submission they are related to
    ref_file = models.ForeignKey(GitFile, null=True, blank=True, on_delete=models.CASCADE, related_name='ref_notes')
    ref_file_type = models.CharField(max_length=14, choices=GitFile.FileTag.choices, blank=True, verbose_name='file type') 
    
    #Instead of having notes attached to edition/curation/verification, we have all notes on submission but track when during the process the note was made.
    #We could have inferred this from the author, but that really stinks for testing as an admin (who can have multiple roles)
    ref_cycle = models.CharField(max_length=12, choices=RefCycle.choices) 
    
    def save(self, *args, **kwargs):
        refs = 0
        refs += (self.ref_file is not None)
        refs += (self.ref_file_type != '')
        if(refs > 1):
            raise AssertionError("Multiple References set")
            
        first_save = False
        if not self.pk:
            first_save = True
            self.manuscript = self.parent_submission.manuscript

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

#If we add any field requirements to software it'll cause issues with our submission form saving.
class VerificationMetadataSoftware(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    #code_repo_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Code Repository URL')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_softwares", blank=True, null=True)
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

class VerificationMetadataBadge(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    badge_type = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Type')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    definition_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Definition URL')
    logo_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Logo URL')
    issuing_org = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Issuing Organization')
    issuing_date = models.DateField(blank=True, null=True, verbose_name='Issuing Date')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_badges")
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

class VerificationMetadataAudit(models.Model):
    name = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Name')
    version = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Version')
    url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='URL')
    organization = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Organization')
    verified_results = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Verified Results')
    exceptions = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Exceptions')
    exception_reason = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Exception Reason')
    verification_metadata = models.ForeignKey('VerificationMetadata', on_delete=models.CASCADE, related_name="verificationmetadata_audits")
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

class VerificationMetadata(AbstractCreateUpdateModel):
    operating_system = models.CharField(max_length=200, default="", verbose_name='Operating System')
    machine_type = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Machine Type')
    scheduler = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Scheduler Module')
    platform = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Platform')
    processor_reqs = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Processor Requirements')
    host_url = models.URLField(max_length=200, default="", blank=True, null=True, verbose_name='Hosting Institution URL')
    memory_reqs = models.CharField(max_length=200, default="", blank=True, null=True, verbose_name='Memory Reqirements')
    packages_info = models.TextField(blank=False, null=False, default="", verbose_name='Required Packages', help_text='Please provide the list of your required packages and their versions.')
    software_info = models.TextField(blank=False, null=False, default="", verbose_name='Statistical Software', help_text='Please provide the list of your used statistical software and their versions.')
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name="submission_vmetadata")
    history = HistoricalRecords(bases=[AbstractHistoryWithChanges,])

#other fields (email, created) are in base model
#see https://github.com/bee-keeper/django-invitations/issues/143 for a bit more info (especially if we want to wire this into admin)
class CorereInvitation(Invitation):
    user = models.OneToOneField('User', on_delete=models.CASCADE, null=True, blank=True, related_name="invite")
    #TODO: connect submission here and cascade on delete

    @classmethod
    def create(cls, email, user, inviter=None, **kwargs):
        key = get_random_string(64).lower()
        instance = cls._default_manager.create(
            email=email,
            user=user,
            key=key,
            inviter=inviter,
            **kwargs)
        return instance

    def send_invitation(self, request, **kwargs):
        current_site = kwargs.pop('site', Site.objects.get_current())
        invite_url = reverse('invitations:accept-invite',
                             args=[self.key])
        
        ##Custom
        if request.is_secure():
            protocol = "https"
        else:
            protocol = "http"
        invite_url = protocol + "://" + settings.SERVER_ADDRESS + invite_url
        ##End Custom

        #invite_url = request.build_absolute_uri(invite_url) #Original        
        ctx = kwargs
        ctx.update({
            'invite_url': invite_url,
            'site_name': current_site.name,
            'email': self.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'key': self.key,
            'inviter': self.inviter,
        })

        email_template = 'invitations/email/email_invite'

        get_invitations_adapter().send_mail(
            email_template,
            self.email,
            ctx)
        self.sent = timezone.now()
        self.save()

        signals.invite_url_sent.send(
            sender=self.__class__,
            instance=self,
            invite_url_sent=invite_url,
            inviter=self.inviter)

############### POST-SAVE ################

# post-save signal to update history with list of fields changed
@receiver(post_save, sender=Manuscript, dispatch_uid="add_history_info_manuscript")
@receiver(post_save, sender=User, dispatch_uid="add_history_info_user")
@receiver(post_save, sender=Submission, dispatch_uid="add_history_info_submission")
@receiver(post_save, sender=Curation, dispatch_uid="add_history_info_curation")
@receiver(post_save, sender=Verification, dispatch_uid="add_history_info_verification")
@receiver(post_save, sender=Note, dispatch_uid="add_history_info_note")
@receiver(post_save, sender=VerificationMetadataSoftware, dispatch_uid="add_history_info_vmetadata_software")
@receiver(post_save, sender=VerificationMetadataBadge, dispatch_uid="add_history_info_vmetadata_badge")
@receiver(post_save, sender=VerificationMetadataAudit, dispatch_uid="add_history_info_vmetadata_audit")
@receiver(post_save, sender=VerificationMetadata, dispatch_uid="add_history_info_vmetadata")
def add_history_info(sender, instance, **kwargs):
    try:
        new_record, old_record = instance.history.order_by('-history_date')[:2]
        delta = new_record.diff_against(old_record)
        new_record.history_change_list = str(delta.changed_fields)
        new_record.save()
    except ValueError:
        pass #On new object creation there are not 2 records to do a history diff on.

#This function is called when a user is added/removed from a group, as well as a group from a user
#Depending on the way this is called, the instance and pk_set will differ
#If this errors out, I think trigger won't be cleared and will error on later saves
@receiver(signal=m2m_changed, sender=User.groups.through)
def signal_handler_when_role_groups_change(instance, action, reverse, model, pk_set, using, *args, **kwargs):
    if settings.CONTAINER_DRIVER == 'wholetale': #TODO-WT: Should I bypass this when self.compute_env != 'Other'? For now I'm just letting it happen. Probably should skip though if only for efficiency
        wtc = w.WholeTaleCorere(admin=True)
        if model is Group and instance.wt_id and not hasattr(instance, 'invite'):
            if action == 'post_add':
                logger.debug("add")
                logger.debug(pk_set)
                for pk in pk_set:
                    try:
                        wtm_group = wtm.GroupConnector.objects.get(corere_group__id=pk)
                        wtc.invite_user_to_group(instance.wt_id, wtm_group.wt_id)
                        logger.debug(f'add {pk}')
                    except wtm.GroupConnector.DoesNotExist:
                        logger.debug(f'Did not add {pk}. Probably because its a "Role Group" that isn\'t in WT')
            elif action == 'post_remove':
                logger.debug("remove")
                for pk in pk_set:
                    try:
                        wtm_group = wtm.GroupConnector.objects.get(corere_group__id=pk)
                        wtc.remove_user_from_group(instance.wt_id, wtm_group.wt_id)
                        logger.debug(f'remove {pk}: wt_user_id {instance.wt_id} , wt_wt_id {wtm_group.wt_id}')
                    except wtm.GroupConnector.DoesNotExist:
                        logger.debug(f'Did not remove {pk}. Probably because its a "Role Group" that isn\'t in WT')                
        if model is User:
            if action == 'post_add':
                logger.debug("add")
                for pk in pk_set:
                    user = User.objects.get(id=pk)
                    logger.debug(f'invite {hasattr(user, "invite")}') #we should expect a new user to have invite
                    if user.wt_id and not hasattr(user, 'invite'):
                        try:
                            wtm_group = wtm.GroupConnector.objects.get(corere_group=instance)
                            wtc.invite_user_to_group(user.wt_id, wtm_group.wt_id)
                            logger.debug(f'add {instance.id}')
                        except wtm.GroupConnector.DoesNotExist:
                            logger.debug(f'Did not add {instance.id}. Probably because its a "Role Group" that isn\'t in WT') 
            elif action == 'post_remove':
                logger.debug("remove")
                for pk in pk_set:
                    user = User.objects.get(id=pk)
                    logger.debug(f'invite {hasattr(user, "invite")}') #we should expect a new user to have invite
                    if user.wt_id and not hasattr(user, 'invite'):
                        try:
                            wtm_group = wtm.GroupConnector.objects.get(corere_group=instance)
                            wtc.invite_user_to_group(user.wt_id, wtm_group.wt_id)
                            logger.debug(f'remove {instance.id}: wt_user_id {user.wt_id} , wt_wt_id {wtm_group.wt_id}')
                        except wtm.GroupConnector.DoesNotExist:
                            logger.debug(f'Did not remove {instance.id}. Probably because its a "Role Group" that isn\'t in WT') 

    else:
        update_groups = []

        #If the user groups are updated via the user admin page, we are just passed back the full user, so we just trigger email updates for each container. Hopefully this isn't too heavy.
        if type(instance) == User:
            update_groups = instance.groups.all()
            #print(instance.groups.all())

        #If a group is added/removed from a user, we are passed the group specifically
        if type(instance) == Group and (action == 'post_remove' or action == 'post_add'):
            update_groups = [instance]

        for group in update_groups:
            #This splits up the group name for checking to see whether its a group we should act upon
            #It would be better to have names formalized someday
            split_name = group.name.split()
            if(len(split_name) == 3):
                [ _, assigned_obj, m_id ] = split_name
                if(assigned_obj == "Manuscript"):
                    manuscript = Manuscript.objects.get(id=m_id)
                    if ((hasattr(manuscript, 'manuscript_localcontainerinfo'))):
                        logger.info("Updating the oauth docker container's list of allowed emails, after changes on this group: " + str(group.name))
                        if (not settings.SKIP_DOCKER):
                            d.update_oauthproxy_container_authenticated_emails(manuscript)