# Generated by Django 3.2.1 on 2021-05-06 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_auto_20210430_1907'),
    ]

    operations = [
        migrations.AddField(
            model_name='containerinfo',
            name='build_in_progress',
            field=models.BooleanField(default=False),
        ),
    ]
