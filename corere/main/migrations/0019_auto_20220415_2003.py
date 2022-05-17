# Generated by Django 3.2.13 on 2022-04-15 20:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_auto_20220415_1911'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_publish_date',
            field=models.DateField(blank=True, help_text='The date the dataset in Dataverse was published', null=True, verbose_name='Dataset Publish Date'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_fetched_publish_date',
            field=models.DateField(blank=True, help_text='The date the dataset in Dataverse was published', null=True, verbose_name='Dataset Publish Date'),
        ),
    ]