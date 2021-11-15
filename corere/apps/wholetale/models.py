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

class TaleGroup(models.Model):
    corere_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="tale_groups")
    wt_group_id = models.CharField(max_length=24, primary_key=True, verbose_name='Group ID in Whole Tale') 

#Global image choices pulled from WT via a manually called admin command
class TaleImageChoice(models.Model):
    choice_id = models.CharField(max_length=24, primary_key=True, verbose_name='Image ID in Whole Tale')
    name = models.CharField(max_length=200, verbose_name='Image Name in Whole Tale')

    def __str__(self):
        return self.name