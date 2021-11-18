from django.db import models
from django.contrib.auth.models import Group
from corere.main import models as m

#Information related to a specific tale remotely hosted in WholeTale
class Tale(models.Model):
    #TODO-WT: this id is probably too long
    tale_id = models.CharField(max_length=24, verbose_name='Tale ID in Whole Tale')
    manuscript = models.OneToOneField(m.Manuscript, on_delete=models.CASCADE, related_name="manuscript_tale")

class TaleVersion(models.Model):
    tale = models.ForeignKey('Tale', on_delete=models.CASCADE, related_name="tale_versions")
    #TODO-WT: this id is probably too long
    container_id = models.CharField(max_length=200, verbose_name='Instance ID for container in Whole Tale')
    container_url = models.URLField(max_length=500, verbose_name='Container URL')
    submission = models.OneToOneField(m.Submission, on_delete=models.CASCADE, related_name="submission_taleversion")
    #TODO: probably add an attribute for the version of the tale in WT

class GroupConnector(models.Model):
    corere_group = models.OneToOneField(Group, blank=True, null=True, on_delete=models.CASCADE, related_name="wholetale_group")
    is_admins = models.BooleanField(default=False) #There is no corere group for admins so we just do this.
    group_id = models.CharField(max_length=24, primary_key=True, verbose_name='Group ID in Whole Tale') 
    group_name = models.CharField(max_length=1024, unique=True, verbose_name='Group Name in Whole Tale') #We store this for ACLs mostly

    def save(self, *args, **kwargs):
        super(GroupConnector, self).save(*args, **kwargs)

        if self.is_admins:
            if self.corere_group:
                raise AssertionError("Admin wholetale groups cannot also be connected to corere_group")

            if GroupConnector.objects.filter(is_admins=True).exclude(group_id=self.group_id).count() > 0:
                raise AssertionError("Only one admin wholetale group can be created")

#Global image choices pulled from WT via a manually called admin command
class ImageChoice(models.Model):
    choice_id = models.CharField(max_length=24, primary_key=True, verbose_name='Image ID in Whole Tale')
    name = models.CharField(max_length=200, verbose_name='Image Name in Whole Tale')

    def __str__(self):
        return self.name