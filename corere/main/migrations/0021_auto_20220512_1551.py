# Generated by Django 3.2.13 on 2022-05-12 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_auto_20220510_2053'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_article_citation',
            field=models.TextField(blank=True, default='', help_text='The article citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Article Citation'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_data_citation',
            field=models.TextField(blank=True, default='', help_text='The data citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Data Citation'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='dataverse_fetched_article_citation',
            field=models.TextField(blank=True, default='', help_text='The article citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Article Citation'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='dataverse_fetched_data_citation',
            field=models.TextField(blank=True, default='', help_text='The data citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Data Citation'),
        ),
    ]
