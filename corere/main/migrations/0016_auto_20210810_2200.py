# Generated by Django 3.2.5 on 2021-08-10 22:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_auto_20210810_2148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='additional_info',
            field=models.TextField(blank=True, default='', help_text='Additional info about the manuscript (e.g., approved exemptions, restricted data, etc).', max_length=1024, null=True, verbose_name='Additional Info'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', max_length=1024, null=True, verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='additional_info',
            field=models.TextField(blank=True, default='', help_text='Additional info about the manuscript (e.g., approved exemptions, restricted data, etc).', max_length=1024, null=True, verbose_name='Additional Info'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', max_length=1024, null=True, verbose_name='Abstract'),
        ),
    ]
