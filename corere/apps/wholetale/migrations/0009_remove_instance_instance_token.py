# Generated by Django 3.2.5 on 2022-01-05 16:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wholetale', '0008_instance_instance_token'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='instance',
            name='instance_token',
        ),
    ]