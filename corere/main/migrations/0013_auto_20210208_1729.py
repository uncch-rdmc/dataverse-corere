# Generated by Django 3.1.6 on 2021-02-08 17:29

import autoslug.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_auto_20210128_2149'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='submission',
            options={'default_permissions': (), 'ordering': ['version_id']},
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='title'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='manuscript',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='title'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='gitlabfile',
            name='tag',
            field=models.CharField(choices=[('code', 'Code'), ('data', 'Data'), ('doc_other', 'Documentation - Other'), ('doc_readme', 'Documentation - Readme'), ('doc_codebook', 'Documentation - Codebook')], max_length=14, verbose_name='file type'),
        ),
    ]