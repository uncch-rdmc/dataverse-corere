# Generated by Django 3.2.11 on 2022-01-24 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wholetale', '0003_rename_choice_id_imagechoice_wt_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='imagechoice',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
