# Generated by Django 3.1.7 on 2021-03-18 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_containerinfo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='containerinfo',
            name='image_id',
        ),
        migrations.AddField(
            model_name='containerinfo',
            name='image_name',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
