# Generated by Django 3.1.7 on 2021-03-09 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20210226_2003'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='author',
            name='position',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='producer_first_name',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='producer_last_name',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='producer_first_name',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='producer_last_name',
        ),
        migrations.RemoveField(
            model_name='verificationmetadatasoftware',
            name='code_repo_url',
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contact_last_name',
            field=models.CharField(blank=True, help_text='Last name of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Contact Last Name'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contact_last_name',
            field=models.CharField(blank=True, help_text='Last name of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Contact Last Name'),
        ),
        migrations.AlterField(
            model_name='verificationmetadata',
            name='operating_system',
            field=models.CharField(default='', max_length=200, verbose_name='Operating System'),
        ),
    ]