from django.db import models
from django.contrib.auth.models import AbstractUser

class Verification(models.Model):
    RESULT_CHOICES = (
        ('', 'Not Attempted'),
        ('', 'Minor Issues'),
        ('', 'Major Issues'),
        ('', 'Success with Modification'),
        ('', 'Success'),
    )
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    date_time = models.DateTimeField() 
    note_text = models.TextField() #TODO: Make this more usable as a list of issues
    software = models.TextField() #TODO: Make this more usable as a list of software

class Curation(models.Model):
    RESULT_CHOICES = (
        ('', 'Materials Incomplete'),
        ('', 'Major Issues'),
        ('', 'Minor Issues'),
        ('', 'No Issues'),
    )
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    date_time = models.DateTimeField()
    note_text = models.TextField()

#Stores metadata
class File(models.Model):
    title = models.TextField()
    md5 = models.CharField(max_length=32)

class Submission(models.Model):
    #MAD: SHOULD THIS HAVE A RESULT?
    files = models.ForeignKey(File, on_delete=models.CASCADE, related_name='files')
    date_time = models.DateTimeField() 

class Manuscript(models.Model):
    pub_id = models.CharField(max_length=200, blank=False, null=False, db_index=True)
    title = models.TextField(blank=False, null=False)
    note_text = models.TextField()
    doi = models.CharField(max_length=200, blank=False, null=False, db_index=True)
    open_data = models.BooleanField(default=False)
    submissions = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="submissions")
    verifications = models.ForeignKey(Verification, on_delete=models.CASCADE, related_name="verifications")
    curations = models.ForeignKey(Curation, on_delete=models.CASCADE, related_name="curations")

    #If I use django fsm will we still use this field?
    STATUS_CHOICES = (
        ('awaiting', 'Awaiting'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    

class User(AbstractUser):
    # This model inherits these fields from abstract user:
    # username, email, first_name, last_name, date_joined and last_login, password, is_superuser, is_staff and is_active

    #NOTE: This approach won't scale great if we need real object-based permissions per manuscript.
    #      But the requirements for the group are pretty well-defined to these roles and this keeps things simple.
    is_author = models.BooleanField(default=False)
    is_editor = models.BooleanField(default=False)
    is_curator = models.BooleanField(default=False)
    is_verifier = models.BooleanField(default=False)

    author_submissions      = models.ManyToManyField(Submission, related_name="author_submissions")
    editor_manuscripts      = models.ManyToManyField(Manuscript, related_name="editor_manuscripts")
    curator_curations       = models.ManyToManyField(Curation, related_name="curator_curations")
    verifier_verifications  = models.ManyToManyField(Verification, related_name="verifier_verifications")

#TODO: Delete this and fix prototype to no longer require it, as its not important for the prototype anyways
class Catalog(models.Model):
    #__tablename__ = 'catalog'
    
    user_id = models.ForeignKey('User', on_delete=models.SET_NULL, null=True) #Do we want orphans?
    status = models.CharField(max_length=250, default="Draft")
    status2 = models.CharField(max_length=250)
    title = models.CharField(max_length=250)
    number = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    collection = models.BooleanField( null=True)
    publish_r = models.BooleanField( default=False)
    publish_a = models.BooleanField( default=False)
    published = models.BooleanField( default=False)
    archive = models.BooleanField( default=False)


    def __repr__(self):
        return '["{}","{}","{}","{}","{}","{}","{}"."{}","{}","{}","{}","{}","{}"]'.format(self.id,self.user_id,self.status,self.status2, self.title, self.number,
        self.created, self.updated, self.collection, self.publish_r, self.publish_a, self.published, self.archive)