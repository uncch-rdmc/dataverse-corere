# Generated by Django 3.2.11 on 2022-01-17 21:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_auto_20220117_2151'),
        ('wholetale', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='groupconnector',
            old_name='group_id',
            new_name='wt_id',
        ),
        migrations.RenameField(
            model_name='instance',
            old_name='container_id',
            new_name='wt_id',
        ),
        migrations.RenameField(
            model_name='tale',
            old_name='tale_id',
            new_name='wt_id',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='container_url',
        ),
        migrations.AddField(
            model_name='instance',
            name='instance_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='Container URL'),
        ),
        migrations.AlterField(
            model_name='tale',
            name='group_connector',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groupconnector_tales', to='wholetale.groupconnector'),
        ),
        migrations.AlterField(
            model_name='tale',
            name='original_tale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tale_copies', to='wholetale.tale'),
        ),
        migrations.AlterField(
            model_name='tale',
            name='submission',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='submission_tales', to='main.submission', verbose_name='The submission whose files are in the tale'),
        ),
        migrations.AlterUniqueTogether(
            name='tale',
            unique_together={('submission', 'group_connector')},
        ),
    ]
