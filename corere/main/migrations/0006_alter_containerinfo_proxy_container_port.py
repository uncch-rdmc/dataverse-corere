# Generated by Django 3.2.1 on 2021-05-14 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_alter_containerinfo_submission_version'),
    ]

    operations = [
        migrations.AlterField(
            model_name='containerinfo',
            name='proxy_container_port',
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),
    ]