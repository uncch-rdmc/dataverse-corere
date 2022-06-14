from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import FieldError
from corere.main import models as m
from urllib.parse import quote_plus

#Information related to a specific tale remotely hosted in WholeTale
class Tale(models.Model):
    wt_id = models.CharField(max_length=24, verbose_name='Tale ID in Whole Tale', unique=True)
    manuscript = models.ForeignKey(m.Manuscript, on_delete=models.CASCADE, related_name="manuscript_tales")
    #Note: Ideally we would require submission but we create original tale before the first submission.
    submission = models.ForeignKey(m.Submission, on_delete=models.CASCADE, null=True, blank=True, related_name="submission_tales", verbose_name='The submission whose files are in the tale')
    original_tale = models.ForeignKey('Tale', on_delete=models.CASCADE, null=True, blank=True, related_name="tale_copies")
    #Each groupconnector should only have one tale
    group_connector = models.ForeignKey('GroupConnector', on_delete=models.CASCADE, related_name="groupconnector_tales")

    class Meta:
        unique_together = ("submission", "group_connector")

    def save(self, *args, **kwargs):
        if self.original_tale:
            if not self.submission:
                #We only enforce this for non-original tales because the original tale is created before the first submission
                raise FieldError("Tales must have a submission set.")
            elif self.original_tale.original_tale:
                raise FieldError("No tale that is an original can have an original itself. A copy cannot be copied again.")

        if(self.pk):
            orig = Tale.objects.get(pk=self.pk)
            if(orig.original_tale != self.original_tale):
                raise FieldError("The original_tale field cannot be modified")

        super(Tale, self).save(*args, **kwargs)

# Only the user in Whole Tale that launches an instance can run it
class Instance(models.Model):
    tale = models.ForeignKey('Tale', on_delete=models.CASCADE, related_name="tale_instances")
    wt_id = models.CharField(max_length=200, verbose_name='Instance ID for container in Whole Tale')
    instance_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='Container URL')
    corere_user = models.ForeignKey(m.User, on_delete=models.CASCADE, related_name="user_instances")
    
    class Meta:
        unique_together = ("tale", "corere_user")

    #This gets the url in the format needed for iframes. This gets the login url that'll then correct set up the user for interaction in the iframe
    def get_login_container_url(self, girderToken):
        return f"https://girder.{settings.WHOLETALE_BASE_URL}/api/v1/user/sign_in?redirect={quote_plus(self.instance_url)}&token={girderToken}"

class GroupConnector(models.Model):
    corere_group = models.OneToOneField(Group, blank=True, null=True, on_delete=models.CASCADE, related_name="wholetale_group")
    is_admins = models.BooleanField(default=False) #There is no corere group for admins so we just do this.
    wt_id = models.CharField(max_length=24, unique=True, verbose_name='Group ID in Whole Tale') 
    manuscript = models.ForeignKey(m.Manuscript, blank=True, null=True, on_delete=models.CASCADE, related_name="manuscript_wtgroups")

    def save(self, *args, **kwargs):
        super(GroupConnector, self).save(*args, **kwargs)

        if self.is_admins:
            if self.corere_group:
                raise AssertionError("Admin wholetale groups cannot also be connected to corere_group")

            if GroupConnector.objects.filter(is_admins=True).exclude(wt_id=self.wt_id).count() > 0:
                raise AssertionError("Only one admin wholetale group can be created")
        else:
            if not self.manuscript:
                raise AssertionError("Non-admin groups must be connected to a Manuscript")

#Global image choices pulled from WT via a manually called admin command
class ImageChoice(models.Model):
    wt_id = models.CharField(max_length=24, primary_key=True, verbose_name='Image ID in Whole Tale')
    name = models.CharField(max_length=200, verbose_name='Image Name in Whole Tale')
    show_last = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['show_last', 'name']

    def __str__(self):
        return self.name