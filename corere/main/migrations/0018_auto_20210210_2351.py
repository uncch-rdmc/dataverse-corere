# Generated by Django 3.1.6 on 2021-02-10 23:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_auto_20210210_2254'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gitfile',
            name='sha1',
        ),
        migrations.AddField(
            model_name='gitfile',
            name='md5',
            field=models.CharField(default='', help_text='Generated cryptographic hash of the file contents. Used to tell if a file has changed between versions.', max_length=32, verbose_name='md5'),
            preserve_default=False,
        ),
    ]
