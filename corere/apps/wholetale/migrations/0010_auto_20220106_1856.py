# Generated by Django 3.2.11 on 2022-01-06 18:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wholetale', '0009_remove_instance_instance_token'),
    ]

    operations = [
        migrations.RenameField(
            model_name='groupconnector',
            old_name='group_id',
            new_name='wt_id',
        ),
        migrations.RenameField(
            model_name='instance',
            old_name='instance_id',
            new_name='wt_id',
        ),
        migrations.RenameField(
            model_name='tale',
            old_name='tale_id',
            new_name='wt_id',
        ),
    ]
