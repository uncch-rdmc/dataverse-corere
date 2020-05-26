import logging
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import FieldError
from django_fsm import FSMField, transition, RETURN_VALUE, has_transition_perm
from corere.main import constants as c
from corere.main.gitlab import gitlab_create_manuscript_repo, gitlab_create_submissions_repo
from guardian.shortcuts import get_users_with_perms, assign_perm
from django.db.models import Q
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from corere.main.middleware import local

logger = logging.getLogger(__name__)  
####################################################

class AbstractCreateUpdateModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="creator_%(class)ss", blank=True, null=True)
    last_editor = models.ForeignKey('User', on_delete=models.SET_NULL, related_name="last_editor_%(class)ss", blank=True, null=True)

    def save(self, *args, **kwargs):
        if hasattr(local, 'user'):
            if(self.pk is None):
                self.creator = local.user
            else:
                self.last_editor = local.user
        return super(AbstractCreateUpdateModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True
        
####################################################

class User(AbstractUser):
    # This model inherits these fields from abstract user:
    # username, email, first_name, last_name, date_joined and last_login, password, is_superuser, is_staff and is_active

    # See apps.py/signals.py for the instantiation of CoReRe's default User groups/permissions

    invite_key = models.CharField(max_length=64, blank=True) # MAD: Should this be encrypted?
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    gitlab_id = models.IntegerField(blank=True, null=True)

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
    _status = FSMField(max_length=15, choices=VERIFICATION_RESULT_CHOICES, default=VERIFICATION_NEW)
    software = models.TextField()
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_verification')

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(self.submission._status != SUBMISSION_IN_PROGRESS_VERIFICATION):
                raise FieldError('A verification cannot be added to a submission unless its status is: ' + SUBMISSION_IN_PROGRESS_VERIFICATION)
        except Verification.submission.RelatedObjectDoesNotExist:
            pass #this is caught in super
        super(Verification, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    def can_edit(self):
        if(self.submission._status == SUBMISSION_IN_PROGRESS_VERIFICATION ):
            return True
        return False

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[can_edit],
        permission=lambda instance, user: user.has_perm('verify_manuscript',instance.submission.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance.submission._status == SUBMISSION_IN_PROGRESS_VERIFICATION and user.has_perm('verify_manuscript',instance.submission.manuscript))
                                            or (instance.submission._status != SUBMISSION_IN_PROGRESS_VERIFICATION and user.has_perm('view_manuscript',instance.submission.manuscript))) )
    def view_noop(self):
        return self._status

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
    _status = FSMField(max_length=15, choices=CURATION_RESULT_CHOICES, default=CURATION_NEW)
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='submission_curation')

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if(self.submission._status != SUBMISSION_IN_PROGRESS_CURATION):
                raise FieldError('A curation cannot be added to a submission unless its status is: ' + SUBMISSION_IN_PROGRESS_CURATION)
        except Curation.submission.RelatedObjectDoesNotExist:
            pass #this is caught in super
        super(Curation, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    def can_edit(self):
        if(self.submission._status == SUBMISSION_IN_PROGRESS_CURATION ):
            return True
        return False

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[can_edit],
        permission=lambda instance, user: user.has_perm('curate_manuscript',instance.submission.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------
    
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance.submission._status == SUBMISSION_IN_PROGRESS_CURATION and user.has_perm('curate_manuscript',instance.submission.manuscript))
                                            or (instance.submission._status != SUBMISSION_IN_PROGRESS_CURATION and user.has_perm('view_manuscript',instance.submission.manuscript))) )
    def view_noop(self):
        return self._status

####################################################

# Before we were just doing new/submitted as technically you can learn the status of the submission from its attached curation/verification.
# But its much easier to find out if any submissions are in progress this way. Maybe we'll switch back to the single point of truth later.

SUBMISSION_NEW = 'new'
SUBMISSION_IN_PROGRESS_CURATION = 'in_progress_curation'
SUBMISSION_IN_PROGRESS_VERIFICATION = 'in_progress_verification'
SUBMISSION_REVIEWED = 'reviewed'

SUBMISSION_RESULT_CHOICES = (
    (SUBMISSION_NEW, 'New'),
    (SUBMISSION_IN_PROGRESS_CURATION, 'In Progress - Curation'),
    (SUBMISSION_IN_PROGRESS_VERIFICATION, 'In Progress - Verification'),
    (SUBMISSION_REVIEWED, 'Reviewed'),
)

#TODO: We should probably have a "uniqueness" check on the object level for submissions incase two users click submit at the same time.
#Our views do check transition permissions first so it'd have to be at the exact same time.
#May also be needed for curation/verification, otherwise you may end up with one that is an orphan.
class Submission(AbstractCreateUpdateModel):
    #Submission does not have a status in itself, its state is inferred by status of curation/verification/manuscript
    _status = FSMField(max_length=25, choices=SUBMISSION_RESULT_CHOICES, default=SUBMISSION_NEW)
    manuscript = models.ForeignKey('Manuscript', on_delete=models.CASCADE, related_name="manuscript_submissions")

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        try:
            if not self.pk: #only first save. Nessecary for submission in progress check but also to allow admin editing of submissions
                if(Submission.objects.filter(manuscript=self.manuscript).exclude(_status=SUBMISSION_REVIEWED).count() > 0):
                    raise FieldError('A submission is already in progress for this manuscript')
                if self.manuscript._status != MANUSCRIPT_AWAITING_INITIAL and self.manuscript._status != MANUSCRIPT_AWAITING_RESUBMISSION:
                    raise FieldError('A submission cannot be created unless a manuscript status is set to await it')
                gitlab_create_submissions_repo(self.manuscript)
        except Submission.manuscript.RelatedObjectDoesNotExist:
            pass #this is caught in super
        super(Submission, self).save(*args, **kwargs)

    ##### django-fsm (workflow) related functions #####

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=SUBMISSION_NEW, target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: user.has_perm('add_submission_to_manuscript',instance.manuscript))
    def edit_noop(self):
        return self._status

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: ((instance._status == SUBMISSION_NEW and user.has_perm('add_submission_to_manuscript',instance.manuscript))
                                            or (instance._status != SUBMISSION_NEW and user.has_perm('view_manuscript',instance.manuscript))) )
    def view_noop(self):
        return self._status

    #-----------------------

    def can_submit(self):
        return True

    @transition(field=_status, source=SUBMISSION_NEW, target=SUBMISSION_IN_PROGRESS_CURATION, on_error=SUBMISSION_NEW, conditions=[can_submit],
                permission=lambda instance, user: user.has_perm('add_submission_to_manuscript',instance.manuscript)) #MAD: Used same perm as add, do we want that?
    def submit(self, user):
        # self.manuscript._status = MANUSCRIPT_PROCESSING
        # self.manuscript.save()
        
        # TODO: This code was switched from doing the above call to nesting transitions. Is there a better way? Does this work right?
        if has_transition_perm(self.manuscript.process, user):
            self.manuscript.process()
            self.manuscript.save()
        else:
            logger.debug("ERROR") #TODO: Handle better
        pass

    #-----------------------

    def can_add_curation(self):
        if(self.manuscript._status != 'processing'):   
            return False
        if(Curation.objects.filter(submission=self).count() > 0): #Using a query because its ok if a new object exists but isn't saved
            return False

        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[SUBMISSION_IN_PROGRESS_CURATION], target=RETURN_VALUE(), conditions=[can_add_curation],
        permission=lambda instance, user: user.has_perm('curate_manuscript',instance.manuscript))
    #TODO: We should actually add the curation to the submission via a parameter instead of being a noop. Also do similar in other places
    def add_curation_noop(self):
        return self._status

    #-----------------------

    def can_add_verification(self):
        if(self.manuscript._status != 'processing'):       
            return False
        try:
            if(self.submission_curation._status != CURATION_NO_ISSUES):
                #print("The curation had issues, so shouldn't be verified")
                return False
        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return False
        if(Verification.objects.filter(submission=self).count() > 0): #Using a query because its ok if a new object exists but isn't saved
            return False
        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[SUBMISSION_IN_PROGRESS_VERIFICATION], target=RETURN_VALUE(), conditions=[can_add_verification],
        permission=lambda instance, user: user.has_perm('verify_manuscript',instance.manuscript))
    def add_verification_noop(self):
        return self._status

    #-----------------------

    #MAD: This whole section may need to be split up to curation/verification to be like "can_submit"
    #... not sure though

    def can_review(self):
        #Note, the logic in here is decided whether you can even do a review, not whether its accepted
        try:
            if(self.submission_curation._status == CURATION_NEW):
                return False
        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return False
        try:
            if(self.submission_verification._status == VERIFICATION_NEW):
                return False
        except Submission.submission_verification.RelatedObjectDoesNotExist:
            pass #we pass because you can review with just a curation
        return True

    #TODO: look over this now that we have to version of SUBMISSION_IN_PROGRESS. Probably can be simplified
    #NOTE: Pretty sure the reason this allows curator and verifier is to check whether this can be reviewed in either flow. Predates dual SUBMISSION_IN_PROGRESS
    @transition(field=_status, source=[SUBMISSION_IN_PROGRESS_CURATION, SUBMISSION_IN_PROGRESS_VERIFICATION], target=RETURN_VALUE(), conditions=[can_review],
                permission=lambda instance, user: ( user.has_perm('curate_manuscript',instance.manuscript)
                    or user.has_perm('verify_manuscript',instance.manuscript) ))
    def review(self):
        try:
            if(self.submission_curation._status == CURATION_NO_ISSUES):
                try:
                    if(self.submission_verification._status == VERIFICATION_SUCCESS):
                        self.manuscript._status = MANUSCRIPT_COMPLETED
                        # Delete existing groups when done for clean-up and reporting
                        # TODO: Update django admin manuscript delete method to delete these groups as well.
                        # It could be even better to extend the group model and have it connected to the manuscript...
                        Group.objects.get(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.manuscript.id)).delete()
                        Group.objects.get(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.manuscript.id)).delete()
                        Group.objects.get(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.manuscript.id)).delete()
                        Group.objects.get(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.manuscript.id)).delete()
                        # MAD: Are we leaving behind any permissions?

                        self.manuscript.save()
                        return SUBMISSION_REVIEWED
                except Submission.submission_verification.RelatedObjectDoesNotExist:
                    return SUBMISSION_IN_PROGRESS_VERIFICATION

        except Submission.submission_curation.RelatedObjectDoesNotExist:
            return SUBMISSION_IN_PROGRESS_CURATION
            
        self.manuscript._status = MANUSCRIPT_AWAITING_RESUBMISSION
        self.manuscript.save()
        return SUBMISSION_REVIEWED

####################################################

MANUSCRIPT_NEW = 'new' 
MANUSCRIPT_AWAITING_INITIAL = 'awaiting_init'
MANUSCRIPT_AWAITING_RESUBMISSION = 'awaiting_resub'
MANUSCRIPT_PROCESSING = 'processing'
MANUSCRIPT_COMPLETED = 'completed'

MANUSCRIPT_STATUS_CHOICES = (
    (MANUSCRIPT_NEW, 'New'),
    (MANUSCRIPT_AWAITING_INITIAL, 'Awaiting Initial Submission'),
    (MANUSCRIPT_AWAITING_RESUBMISSION, 'Awaiting Resubmission'),
    (MANUSCRIPT_PROCESSING, 'Processing Submission'),
    (MANUSCRIPT_COMPLETED, 'Completed'),
)

class Manuscript(AbstractCreateUpdateModel):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) #currently only used for naming a file folder on upload. Needed as id doesn't exist until after create
    pub_id = models.CharField(max_length=200, default="", db_index=True)
    title = models.TextField(blank=False, null=False, default="")
    doi = models.CharField(max_length=200, default="", db_index=True)
    open_data = models.BooleanField(default=False)
    environment_info = JSONField(encoder=DjangoJSONEncoder, default=list, blank=True, null=True)
    gitlab_manuscript_id = models.IntegerField(blank=True, null=True) #Storing the repo for manuscript files
    gitlab_submissions_id = models.IntegerField(blank=True, null=True) #Storing the repo for submission files (all submissions)
    _status = FSMField(max_length=15, choices=MANUSCRIPT_STATUS_CHOICES, default=MANUSCRIPT_NEW)

    def __str__(self):
        return '{0}: {1}'.format(self.id, self.title)

    class Meta:
        permissions = [
            #TODO: This includes default CRUD permissions, but we should switch it to be explicit (other objects too)
            ('manage_authors_on_manuscript', 'Can manage authors on manuscript'),
            ('manage_editors_on_manuscript', 'Can manage editors on manuscript'),
            ('manage_curators_on_manuscript', 'Can manage curators on manuscript'),
            ('manage_verifiers_on_manuscript', 'Can manage verifiers on manuscript'),
            ('add_submission_to_manuscript', 'Can add submission to manuscript'),
            #('review_submission_on_manuscript', 'Can review submission on manuscript'),
            # We track permissions of objects under the manuscript at the manuscript level, as we don't need to be more granular
            # Technically curation/verification are added to a submission
            ('curate_manuscript', 'Can curate manuscript/submission'),
            ('verify_manuscript', 'Can verify manuscript/submission'),
        ]

    def save(self, *args, **kwargs):
        first_save = False
        if not self.pk:
            first_save = True
        super(Manuscript, self).save(*args, **kwargs)
        if first_save:
            # Note these works alongside global permissions defined in signals.py
            # TODO: Make this concatenation standardized
            group_manuscript_editor, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_EDITOR_PREFIX + " " + str(self.id))
            assign_perm('change_manuscript', group_manuscript_editor, self) 
            assign_perm('delete_manuscript', group_manuscript_editor, self) 
            assign_perm('view_manuscript', group_manuscript_editor, self) 
            assign_perm('manage_authors_on_manuscript', group_manuscript_editor, self) 

            group_manuscript_author, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.id))
            assign_perm('change_manuscript', group_manuscript_author, self)
            assign_perm('view_manuscript', group_manuscript_author, self) 
            assign_perm('manage_authors_on_manuscript', group_manuscript_author, self) 
            assign_perm('add_submission_to_manuscript', group_manuscript_author, self) 

            group_manuscript_curator, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(self.id))
            assign_perm('change_manuscript', group_manuscript_curator, self) 
            assign_perm('view_manuscript', group_manuscript_curator, self) 
            assign_perm('curate_manuscript', group_manuscript_curator, self) 

            group_manuscript_verifier, created = Group.objects.get_or_create(name=c.GROUP_MANUSCRIPT_VERIFIER_PREFIX + " " + str(self.id))
            assign_perm('change_manuscript', group_manuscript_verifier, self) 
            assign_perm('view_manuscript', group_manuscript_verifier, self) 
            assign_perm('verify_manuscript', group_manuscript_verifier, self) 

            group_manuscript_editor.user_set.add(local.user) #TODO: Should be dynamic on role or more secure, but right now only editors create manuscripts

            gitlab_create_manuscript_repo(self)

            
    ##### django-fsm (workflow) related functions #####

    #Conditions: Authors needed, files uploaded [NOT DONE]
    def can_begin(self):
        # Are there any authors assigned to the manuscript?
        group_string = name=c.GROUP_MANUSCRIPT_AUTHOR_PREFIX + " " + str(self.id)
        count = User.objects.filter(groups__name=group_string).count()
        if(count < 1):
            return False
        return True

    @transition(field=_status, source=MANUSCRIPT_NEW, target=MANUSCRIPT_AWAITING_INITIAL, conditions=[can_begin],
                permission=lambda instance, user: user.has_perm('change_manuscript',instance))
    def begin(self):
        pass #Here add any additional actions related to the state change

    #-----------------------

    def can_add_submission(self):
        # Technically we don't need to check 'in_progress' as in that case the manuscript will be processing, but redundancy is ok
        #try:
        if (self.manuscript_submissions.filter(Q(_status='new')| Q(_status='in_progress')).count() != 0):
            return False
        #except Manuscript.manuscript_submissions.RelatedObjectDoesNotExist:
        #   pass
        return True

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[MANUSCRIPT_AWAITING_INITIAL, MANUSCRIPT_AWAITING_RESUBMISSION], target=RETURN_VALUE(), conditions=[can_add_submission],
                permission=lambda instance, user: user.has_perm('add_submission_to_manuscript',instance))
    def add_submission_noop(self):
        return self._status

    #-----------------------

    #Conditions: Submission with status of new
    def can_process(self):
        #print("OHNO: "+ str(self.manuscript_submissions.filter(_status='new').count()))

        if(self.manuscript_submissions.filter(_status='new').count() != 1):
            return False
        return True

    # Perm: ability to create/edit a submission
    @transition(field=_status, source=[MANUSCRIPT_AWAITING_INITIAL, MANUSCRIPT_AWAITING_RESUBMISSION], target=MANUSCRIPT_PROCESSING, conditions=[can_process],
                permission=lambda instance, user: user.has_perm('add_submission_to_manuscript',instance))
    def process(self):
        #update submission status here?
        pass #Here add any additional actions related to the state change

    #-----------------------

    #Does not actually change status, used just for permission checking
    @transition(field=_status, source=[MANUSCRIPT_NEW, MANUSCRIPT_AWAITING_INITIAL, MANUSCRIPT_AWAITING_RESUBMISSION], target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: user.has_perm('change_manuscript',instance))
    def edit_noop(self):
        return self._status

    #-----------------------

    #TODO: Address limitation with having only one manuscript version. If its being edited as part of a resubmission what do we do about viewing?
    #      Do we just allow viewing whatever is there? Do we block it during certain states. Maybe it'll be less of an issue if we can put all versioned data in the submission?
    #
    #Does not actually change status, used just for permission checking
    @transition(field=_status, source='*', target=RETURN_VALUE(), conditions=[],
        permission=lambda instance, user: (#(instance._status == MANUSCRIPT_NEW and user.has_perm('add_manuscript',instance.manuscript)) or #add_manuscript means any other editor can see it (even from a different pub...)
                                            (instance._status != MANUSCRIPT_NEW and user.has_perm('view_manuscript',instance))) )
    def view_noop(self):
        return self._status


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

#TODO:
# - Multiple files?
#   - Instead can I just allow note duplication?
# - Scoping based upon permissions? groups?]
#   - I want to say on creation which types of users can view the note
#   - Could add object based view permissions to the groups? (e.g. these groups: c.GROUP_MANUSCRIPT_CURATOR_PREFIX + " " + str(manuscript.id))
#       - ... so on create, assign 1-4 perms per note
#       - Let's think about how we'll be using this:
#           - Creating notes: assing 'view note' object based perm to each group that has access
#           - Displaying notes: Just call get_objects_for_user
#               - ... not true when displaing notes connected to specific object. Gotta get all notes and check perms on each
#           - Displaying scope of notes: use perm and get each group associated (reverse m2m lookup)
# I should also be thinking about this in the context of tags?

class Note(AbstractCreateUpdateModel):
    text = models.TextField(default="")

    parent_submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    parent_curation = models.ForeignKey(Curation, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    parent_verification = models.ForeignKey(Verification, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')
    parent_file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE, related_name='notes')

    #note this is not a "parent" relationship like above
    manuscript = models.ForeignKey(Manuscript, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def parent(self):
        if self.parent_submission_id is not None:
            return self.parent_submission
        if self.parent_curation_id is not None:
            return self.parent_curation
        if self.parent_verification_id is not None:
            return self.parent_verification
        if self.parent_file_id is not None:
            return self.parent_file
        raise AssertionError("Neither 'parent_submission', 'parent_curation', 'parent_verification' or 'parent_file' is set")
    
    def save(self, *args, **kwargs):
        parents = 0
        parents += (self.parent_submission_id is not None)
        parents += (self.parent_curation_id is not None)
        parents += (self.parent_verification_id is not None)
        if(parents > 1):
            raise AssertionError("Multiple parents set")

        first_save = False
        if not self.pk:
            first_save = True
        super(Note, self).save(*args, **kwargs)
        #print("auth: "+ str(local.user.is_authenticated))
        if first_save and local.user != None and local.user.is_authenticated: #maybe redundant
            ## MAD: Disabled this code as I think it was the same as the scope code in the form
            # group_prefixes = kwargs.pop('group_prefixes', [])
            # print("group_prefixes")
            # print(group_prefixes)
            # for prefix in group_prefixes:
            #     group = Group.objects.get(name=prefix + " " + str(self.manuscript.id))
            #     assign_perm('view_note', prefix, self) 

            #user always has full permissions to their own note
            #print("ASSIGN PERM MODEL")
            #print(local.user.__dict__)
            assign_perm('view_note', local.user, self) 
            assign_perm('change_note', local.user, self) 
            assign_perm('delete_note', local.user, self) 

    #TODO: If implementing fsm can_edit, base it upon the creator of the note
