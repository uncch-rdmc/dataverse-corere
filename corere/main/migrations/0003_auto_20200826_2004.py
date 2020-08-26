# Generated by Django 2.2.15 on 2020-08-26 20:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20200820_1834'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='gitlabfile',
            name='main_gitlab_gitlab__6b2352_idx',
        ),
        migrations.RenameField(
            model_name='gitlabfile',
            old_name='gitlab_sha1',
            new_name='gitlab_blob_id',
        ),
        migrations.AlterField(
            model_name='gitlabfile',
            name='parent_manuscript',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='file_manuscript', to='main.Manuscript'),
        ),
        migrations.AddIndex(
            model_name='gitlabfile',
            index=models.Index(fields=['gitlab_blob_id', 'parent_submission'], name='main_gitlab_gitlab__a99b89_idx'),
        ),
    ]
