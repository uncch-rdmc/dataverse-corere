# Generated by Django 3.2.13 on 2022-06-01 21:55

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20220214_2138'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataverseInstallation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Installation Name')),
                ('url', models.URLField(verbose_name='URL')),
                ('api_token', models.CharField(max_length=200, verbose_name='API Token')),
                ('username', models.CharField(blank=True, default='', help_text='User that owns the API token. We store this only for informational purposes.', max_length=200, null=True, verbose_name='User Name')),
            ],
        ),
        migrations.RemoveField(
            model_name='verificationmetadata',
            name='creator',
        ),
        migrations.RemoveField(
            model_name='verificationmetadata',
            name='last_editor',
        ),
        migrations.RemoveField(
            model_name='verificationmetadata',
            name='manuscript',
        ),
        migrations.AlterModelOptions(
            name='manuscript',
            options={'permissions': [('change_manuscript_files', 'Can manage files for a manuscript'), ('add_authors_on_manuscript', 'Can manage authors on manuscript'), ('remove_authors_on_manuscript', 'Can manage authors on manuscript'), ('manage_editors_on_manuscript', 'Can manage editors on manuscript'), ('manage_curators_on_manuscript', 'Can manage curators on manuscript'), ('manage_verifiers_on_manuscript', 'Can manage verifiers on manuscript'), ('add_submission_to_manuscript', 'Can add submission to manuscript'), ('approve_manuscript', 'Can review submissions for processing'), ('curate_manuscript', 'Can curate manuscript/submission'), ('verify_manuscript', 'Can verify manuscript/submission')]},
        ),
        migrations.RenameField(
            model_name='historicalmanuscript',
            old_name='dataverse_doi',
            new_name='dataverse_fetched_doi',
        ),
        migrations.RenameField(
            model_name='manuscript',
            old_name='dataverse_doi',
            new_name='dataverse_fetched_doi',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='additional_info',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='contents_proprietary',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='contents_proprietary_sharing',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='additional_info',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='contents_proprietary',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='contents_proprietary_sharing',
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='contents_restricted',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='contents_restricted_sharing',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_article_citation',
            field=models.TextField(blank=True, default='', help_text='The article citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Article Citation'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_data_citation',
            field=models.TextField(blank=True, default='', help_text='The data citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Data Citation'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_fetched_publish_date',
            field=models.DateField(blank=True, help_text='The date the dataset in Dataverse was published', null=True, verbose_name='Dataset Publish Date'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_parent',
            field=models.CharField(blank=True, default='', help_text='The parent Dataverse on the installation that your new dataset will be created under. Please provide the name at the end of the dataverse page URL (e.g. https://dataverse.unc.edu/dataverse/COPY_THIS_NAME)', max_length=1024, null=True, verbose_name='Parent Dataverse'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='exemption_override',
            field=models.BooleanField(default=False, help_text='The curation team has decided to deploy this manuscript inside Whole Tale, even with potential issues.', verbose_name='Exemption Override'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='host_url',
            field=models.URLField(blank=True, default='', null=True, verbose_name='Hosting Institution URL'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='machine_type',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Machine Type'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='memory_reqs',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Memory Reqirements'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='operating_system',
            field=models.CharField(default='', max_length=200, verbose_name='Operating System'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='other_exemptions',
            field=models.TextField(blank=True, default='', help_text='Are there any other exemptions to the verification workflow that the curation team should know about?', max_length=1024, null=True, verbose_name='Other Exemptions'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='packages_info',
            field=models.TextField(default='', help_text='Please provide the list of your required packages and their versions.', verbose_name='Required Packages'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='platform',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Platform'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='processor_reqs',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Processor Requirements'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='scheduler',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Scheduler Module'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='software_info',
            field=models.TextField(default='', help_text='Please provide the list of your used statistical software and their versions.', verbose_name='Statistical Software'),
        ),
        migrations.AddField(
            model_name='historicalsubmission',
            name='editor_submit_date',
            field=models.DateField(blank=True, help_text='The date when editors submitted the submission. Only used when editor use of CORE2 for a manuscript is disabled.', null=True, verbose_name='Editor Submit Date'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='contents_restricted',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='contents_restricted_sharing',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_fetched_article_citation',
            field=models.TextField(blank=True, default='', help_text='The article citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Article Citation'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_fetched_data_citation',
            field=models.TextField(blank=True, default='', help_text='The data citation pulled from the dataset connected to this manuscript (via DOI)', null=True, verbose_name='Dataverse Data Citation'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_fetched_publish_date',
            field=models.DateField(blank=True, help_text='The date the dataset in Dataverse was published', null=True, verbose_name='Dataset Publish Date'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_parent',
            field=models.CharField(blank=True, default='', help_text='The parent Dataverse on the installation that your new dataset will be created under. Please provide the name at the end of the dataverse page URL (e.g. https://dataverse.unc.edu/dataverse/COPY_THIS_NAME)', max_length=1024, null=True, verbose_name='Parent Dataverse'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='exemption_override',
            field=models.BooleanField(default=False, help_text='The curation team has decided to deploy this manuscript inside Whole Tale, even with potential issues.', verbose_name='Exemption Override'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='host_url',
            field=models.URLField(blank=True, default='', null=True, verbose_name='Hosting Institution URL'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='machine_type',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Machine Type'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='memory_reqs',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Memory Reqirements'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='operating_system',
            field=models.CharField(default='', max_length=200, verbose_name='Operating System'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='other_exemptions',
            field=models.TextField(blank=True, default='', help_text='Are there any other exemptions to the verification workflow that the curation team should know about?', max_length=1024, null=True, verbose_name='Other Exemptions'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='packages_info',
            field=models.TextField(default='', help_text='Please provide the list of your required packages and their versions.', verbose_name='Required Packages'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='platform',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Platform'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='processor_reqs',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Processor Requirements'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='scheduler',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Scheduler Module'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='software_info',
            field=models.TextField(default='', help_text='Please provide the list of your used statistical software and their versions.', verbose_name='Statistical Software'),
        ),
        migrations.AddField(
            model_name='submission',
            name='editor_submit_date',
            field=models.DateField(blank=True, help_text='The date when editors submitted the submission. Only used when editor use of CORE2 for a manuscript is disabled.', null=True, verbose_name='Editor Submit Date'),
        ),
        migrations.AlterField(
            model_name='curation',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('incomplete_materials', 'Incomplete Materials'), ('major_issues', 'Major Issues'), ('minor_issues', 'Minor Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the curator', max_length=32, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='gitfile',
            name='tag',
            field=models.CharField(blank=True, choices=[('code', 'Code'), ('data', 'Data'), ('documentation_readme', 'Documentation - Readme'), ('documentation_codebook', 'Documentation - Codebook'), ('documentation_other', 'Documentation - Other')], max_length=32, null=True, verbose_name='file type'),
        ),
        migrations.AlterField(
            model_name='historicalcuration',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('incomplete_materials', 'Incomplete Materials'), ('major_issues', 'Major Issues'), ('minor_issues', 'Minor Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the curator', max_length=32, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('awaiting_initial', 'Awaiting Initial Submission'), ('awaiting_resubmission', 'Awaiting Author Resubmission'), ('reviewing', 'Editor Reviewing'), ('processing', 'Processing Submission'), ('pending_dataverse_publish', 'Pending Dataverse Publish'), ('published_to_dataverse', 'Published To Dataverse'), ('completed_report_sent', 'Completed Report Sent')], default='new', help_text='The overall status of the manuscript in the review process', max_length=32, verbose_name='Manuscript Status'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', null=True, verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='high_performance',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript require a high-performance compute environment?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qdr_review',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript need verification of qualitative results by QDR?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qual_analysis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript include qualitative analysis?'),
        ),
        migrations.AlterField(
            model_name='historicalnote',
            name='ref_cycle',
            field=models.CharField(choices=[('submission', 'Submission'), ('edition', 'Edition'), ('curation', 'Curation'), ('verification', 'Verification')], max_length=32),
        ),
        migrations.AlterField(
            model_name='historicalnote',
            name='ref_file_type',
            field=models.CharField(blank=True, choices=[('code', 'Code'), ('data', 'Data'), ('documentation_readme', 'Documentation - Readme'), ('documentation_codebook', 'Documentation - Codebook'), ('documentation_other', 'Documentation - Other')], max_length=32, verbose_name='file type'),
        ),
        migrations.AlterField(
            model_name='historicalsubmission',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('in_progress_edition', 'In Progress Edition'), ('rejected_editor', 'Rejected Editor'), ('in_progress_curation', 'In Progress Curation'), ('in_progress_verification', 'In Progress Verification'), ('reviewed_awaiting_report', 'Reviewed Awaiting Report'), ('reviewed_awaiting_approval', 'Reviewed Report Awaiting Approval'), ('returned', 'Returned')], default='new', help_text='The status of the submission in the review process', max_length=32, verbose_name='Submission review status'),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='email',
            field=models.EmailField(db_index=True, max_length=254, validators=[django.core.validators.EmailValidator]),
        ),
        migrations.AlterField(
            model_name='historicalverification',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('not_attempted', 'Not Attempted'), ('minor_issues', 'Minor Issues'), ('major_issues', 'Major Issues'), ('success_with_modification', 'Success with Modification'), ('success', 'Success')], default='new', help_text='Was the submission able to be verified', max_length=32, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('awaiting_initial', 'Awaiting Initial Submission'), ('awaiting_resubmission', 'Awaiting Author Resubmission'), ('reviewing', 'Editor Reviewing'), ('processing', 'Processing Submission'), ('pending_dataverse_publish', 'Pending Dataverse Publish'), ('published_to_dataverse', 'Published To Dataverse'), ('completed_report_sent', 'Completed Report Sent')], default='new', help_text='The overall status of the manuscript in the review process', max_length=32, verbose_name='Manuscript Status'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', null=True, verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='high_performance',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript require a high-performance compute environment?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qdr_review',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript need verification of qualitative results by QDR?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qual_analysis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript include qualitative analysis?'),
        ),
        migrations.AlterField(
            model_name='note',
            name='ref_cycle',
            field=models.CharField(choices=[('submission', 'Submission'), ('edition', 'Edition'), ('curation', 'Curation'), ('verification', 'Verification')], max_length=32),
        ),
        migrations.AlterField(
            model_name='note',
            name='ref_file_type',
            field=models.CharField(blank=True, choices=[('code', 'Code'), ('data', 'Data'), ('documentation_readme', 'Documentation - Readme'), ('documentation_codebook', 'Documentation - Codebook'), ('documentation_other', 'Documentation - Other')], max_length=32, verbose_name='file type'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('in_progress_edition', 'In Progress Edition'), ('rejected_editor', 'Rejected Editor'), ('in_progress_curation', 'In Progress Curation'), ('in_progress_verification', 'In Progress Verification'), ('reviewed_awaiting_report', 'Reviewed Awaiting Report'), ('reviewed_awaiting_approval', 'Reviewed Report Awaiting Approval'), ('returned', 'Returned')], default='new', help_text='The status of the submission in the review process', max_length=32, verbose_name='Submission review status'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True, validators=[django.core.validators.EmailValidator]),
        ),
        migrations.AlterField(
            model_name='verification',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('not_attempted', 'Not Attempted'), ('minor_issues', 'Minor Issues'), ('major_issues', 'Major Issues'), ('success_with_modification', 'Success with Modification'), ('success', 'Success')], default='new', help_text='Was the submission able to be verified', max_length=32, verbose_name='Review'),
        ),
        migrations.DeleteModel(
            name='HistoricalVerificationMetadata',
        ),
        migrations.DeleteModel(
            name='VerificationMetadata',
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='dataverse_installation',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.dataverseinstallation', verbose_name='Dataverse Installation'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='dataverse_installation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dataverseinstallation_manuscripts', to='main.dataverseinstallation', verbose_name='Dataverse Installation'),
        ),
    ]