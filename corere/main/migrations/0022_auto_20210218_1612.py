# Generated by Django 3.1.6 on 2021-02-18 16:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_remove_historicalmanuscript_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gitfile',
            name='path',
            field=models.CharField(help_text='The path of the folders holding the file, not including the filename', max_length=4096, verbose_name='file path'),
        ),
    ]