# Generated by Django 3.2.12 on 2022-03-12 18:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_auto_20220311_1747'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='manuscript',
            options={'permissions': [('change_manuscript_files', 'Can manage files for a manuscript'), ('add_authors_on_manuscript', 'Can manage authors on manuscript'), ('remove_authors_on_manuscript', 'Can manage authors on manuscript'), ('manage_editors_on_manuscript', 'Can manage editors on manuscript'), ('manage_curators_on_manuscript', 'Can manage curators on manuscript'), ('manage_verifiers_on_manuscript', 'Can manage verifiers on manuscript'), ('add_submission_to_manuscript', 'Can add submission to manuscript'), ('approve_manuscript', 'Can review submissions for processing'), ('curate_manuscript', 'Can curate manuscript/submission'), ('verify_manuscript', 'Can verify manuscript/submission')]},
        ),
    ]