# Generated by Django 3.1.6 on 2021-02-10 22:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_auto_20210210_2242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gitfile',
            name='date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='file creation date'),
        ),
    ]