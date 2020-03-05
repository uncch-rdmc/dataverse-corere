# Generated by Django 2.2.10 on 2020-03-05 21:09

from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_auto_20200303_2357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='parent_curation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='curation_notes', to='main.Curation'),
        ),
        migrations.AlterField(
            model_name='note',
            name='parent_file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='file_notes', to='main.File'),
        ),
        migrations.AlterField(
            model_name='note',
            name='parent_submission',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='submission_notes', to='main.Submission'),
        ),
        migrations.AlterField(
            model_name='note',
            name='parent_verification',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verification_notes', to='main.Verification'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('in_progress_verification', 'In Progress - Curation'), ('in_progress_curation', 'In Progress - Verification'), ('reviewed', 'Reviewed')], default='new', max_length=25),
        ),
    ]
