from django.db import models
from django.contrib.auth.models import Group
from django.core.exceptions import FieldError
from corere.main import models as m

#Information related to a specific tale remotely hosted in WholeTale
class Tale(models.Model):
    #TODO-WT: this id (and probably all the other WT ones) are probably too long
    #TODO-WT: maybe we should rename this to wt_id. Maybe we should do this for all models?
    tale_id = models.CharField(max_length=24, verbose_name='Tale ID in Whole Tale', unique=True)
    manuscript = models.ForeignKey(m.Manuscript, on_delete=models.CASCADE, related_name="manuscript_tales")
    #TODO-WT: I wanted to require submission but we create original tale before the first submission.
    submission = models.ForeignKey(m.Submission, on_delete=models.CASCADE, null=True, blank=True, related_name="submission_tales", verbose_name='The submission whose files are in the tale')
    original_tale = models.ForeignKey('Tale', on_delete=models.CASCADE, null=True, blank=True, related_name="tale_copies")
    #Each groupconnector should only have one tale
    group_connector = models.OneToOneField('GroupConnector', on_delete=models.CASCADE, related_name="groupconnector_tale")
    # latest_version_id = models.CharField(max_length=24, unique=True, verbose_name='Active Version ID in Whole Tale')

    def save(self, *args, **kwargs):
        print(self.__dict__)
        print(self.original_tale)
        if self.original_tale:
            if not self.submission:
                #NOTE: We only enforce this for non-original tales because the original tale is created before the first submission
                raise FieldError("Tales must have a submission set.")
            elif self.original_tale.original_tale:
                raise FieldError("No tale that is an original can have an original itself. A copy cannot be copied again.")

        if(self.pk):
            orig = Tale.objects.get(pk=self.pk)
            if(orig.original_tale != self.original_tale):
                #TODO-WT: Make field read-only in admin?
                raise FieldError("The original_tale field cannot be modified")

        super(Tale, self).save(*args, **kwargs)

## Instead of storing versions as a separate object, we'll just store the submission with the tale. For the original tale this will mean the latest

# class TaleVersion(models.Model):
#     tale = models.ForeignKey('Tale', on_delete=models.CASCADE, related_name="tale_versions")
#     version_id = models.CharField(max_length=24, unique=True, verbose_name='Version ID in Whole Tale')
#     submission = models.OneToOneField(m.Submission, on_delete=models.CASCADE, related_name="submission_taleversion")

#     class Meta:
#         unique_together = ("tale", "submission")

#     def save(self, *args, **kwargs):
#         if self.tale.original_tale is not None:
#             raise FieldError("Only a original tale can track TaleVersions")
#         super(TaleVersion, self).save(*args, **kwargs)

# Only the user in Whole Tale that launches an instance can run it
class Instance(models.Model):
    tale = models.ForeignKey('Tale', on_delete=models.CASCADE, related_name="tale_instances") #maybe unnessecary with tale_verison
    #tale_version = models.ForeignKey('TaleVersion', on_delete=models.CASCADE, related_name="taleversion_instances")
    
    container_id = models.CharField(max_length=200, verbose_name='Instance ID for container in Whole Tale')
    container_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='Container URL')
    corere_user = models.ForeignKey(m.User, on_delete=models.CASCADE, related_name="user_instances")
    
    #TODO-WT: Add accessor method to get the FULL container_url
    
    class Meta: #TODO-WT: I think this is the right approach. Each user should only have one instance per tale
        unique_together = ("tale", "corere_user")

    def get_full_container_url(self):
        #TODO-WT: Implement this getting the right info from settings
        #TODO-WT: I may actually be storing the full URL already, WITH the token. Which seems bad.
        return self.container_url

class GroupConnector(models.Model):
    corere_group = models.OneToOneField(Group, blank=True, null=True, on_delete=models.CASCADE, related_name="wholetale_group")
    is_admins = models.BooleanField(default=False) #There is no corere group for admins so we just do this.
    group_id = models.CharField(max_length=24, unique=True, verbose_name='Group ID in Whole Tale') 
    #group_name = models.CharField(max_length=1024, unique=True, verbose_name='Group Name in Whole Tale') #We store this for ACLs mostly
    manuscript = models.ForeignKey(m.Manuscript, blank=True, null=True, on_delete=models.CASCADE, related_name="manuscript_wtgroups")

    def save(self, *args, **kwargs):
        super(GroupConnector, self).save(*args, **kwargs)

        if self.is_admins:
            if self.corere_group:
                raise AssertionError("Admin wholetale groups cannot also be connected to corere_group")

            if GroupConnector.objects.filter(is_admins=True).exclude(group_id=self.group_id).count() > 0:
                raise AssertionError("Only one admin wholetale group can be created")
        else:
            if not self.manuscript:
                raise AssertionError("Non-admin groups must be connected to a Manuscript")

    #This could also build it from our constructor method, but for now we use the same names for both so this is easiest
    #TODO-WT: Do I really need both this and the function in wholetale_corere?
    def get_wt_group_name(self):
        return self.corere_group.name

#Global image choices pulled from WT via a manually called admin command
class ImageChoice(models.Model):
    choice_id = models.CharField(max_length=24, primary_key=True, verbose_name='Image ID in Whole Tale')
    name = models.CharField(max_length=200, verbose_name='Image Name in Whole Tale')

    def __str__(self):
        return self.name


#   So what am I doing to support tale-per-group?
#   - One tale can have multiple instances. This happens when multiple users have write access to the same tale and launch.
#       - Instances are ALWAYS per-user
#   - One submission can have multiple tales. Each group will have its own tale. The authors tale is the original and the other's are copies
#       - Do we need to retain previous versions of non-author tales? I think not.
#       - What happens programatically when a verifier launches the previous version of a tale? Do we have to support this?
#           - What happens when an AUTHOR launches a previous version? Do we have to do extra things to prevent writing? I think not but doublecheck
#   - The author tale will be versioned as it is updated

#   - How am I tracking the distinction between "master" tales and "copy" tales?
#       - When copying, we are always planning to copy as a group right?