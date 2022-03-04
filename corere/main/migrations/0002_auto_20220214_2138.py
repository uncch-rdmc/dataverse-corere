# Generated by Django 3.2.12 on 2022-02-14 21:38

import autoslug.fields
import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('invitations', '0003_auto_20151126_1523'),
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorereInvitation',
            fields=[
                ('invitation_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='invitations.invitation')),
            ],
            options={
                'abstract': False,
            },
            bases=('invitations.invitation',),
        ),
        migrations.CreateModel(
            name='LocalContainerInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repo_image_name', models.CharField(blank=True, max_length=128, null=True)),
                ('proxy_image_name', models.CharField(blank=True, max_length=128, null=True)),
                ('repo_container_id', models.CharField(blank=True, max_length=64, null=True)),
                ('repo_container_ip', models.CharField(blank=True, max_length=24, null=True)),
                ('proxy_container_id', models.CharField(blank=True, max_length=64, null=True)),
                ('proxy_container_address', models.CharField(blank=True, max_length=24, null=True)),
                ('proxy_container_port', models.IntegerField(blank=True, null=True, unique=True)),
                ('network_ip_substring', models.CharField(blank=True, max_length=12, null=True)),
                ('network_id', models.CharField(blank=True, max_length=64, null=True)),
                ('submission_version', models.IntegerField(blank=True, null=True)),
                ('build_in_progress', models.BooleanField(default=False)),
            ],
        ),
        migrations.RemoveField(
            model_name='historicalverificationmetadatasoftware',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalverificationmetadatasoftware',
            name='verification_metadata',
        ),
        migrations.RemoveField(
            model_name='verificationmetadatasoftware',
            name='verification_metadata',
        ),
        migrations.RenameField(
            model_name='historicalmanuscript',
            old_name='title',
            new_name='pub_name',
        ),
        migrations.RenameField(
            model_name='manuscript',
            old_name='title',
            new_name='pub_name',
        ),
        migrations.RemoveField(
            model_name='historicalsubmission',
            name='contents_gis',
        ),
        migrations.RemoveField(
            model_name='historicalsubmission',
            name='contents_proprietary',
        ),
        migrations.RemoveField(
            model_name='historicalsubmission',
            name='contents_proprietary_sharing',
        ),
        migrations.RemoveField(
            model_name='historicalsubmission',
            name='high_performance',
        ),
        migrations.RemoveField(
            model_name='historicaluser',
            name='invite_key',
        ),
        migrations.RemoveField(
            model_name='historicalverificationmetadata',
            name='submission',
        ),
        migrations.RemoveField(
            model_name='historicalverificationmetadataaudit',
            name='verification_metadata',
        ),
        migrations.RemoveField(
            model_name='historicalverificationmetadatabadge',
            name='verification_metadata',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='contents_gis',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='contents_proprietary',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='contents_proprietary_sharing',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='high_performance',
        ),
        migrations.RemoveField(
            model_name='user',
            name='invite_key',
        ),
        migrations.RemoveField(
            model_name='verificationmetadata',
            name='submission',
        ),
        migrations.RemoveField(
            model_name='verificationmetadataaudit',
            name='verification_metadata',
        ),
        migrations.RemoveField(
            model_name='verificationmetadatabadge',
            name='verification_metadata',
        ),
        migrations.AddField(
            model_name='curation',
            name='needs_verification',
            field=models.BooleanField(default=False, verbose_name='Needs Verification'),
        ),
        migrations.AddField(
            model_name='historicalcuration',
            name='needs_verification',
            field=models.BooleanField(default=False, verbose_name='Needs Verification'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='additional_info',
            field=models.TextField(blank=True, default='', help_text='Additional info about the manuscript (e.g., approved exemptions, restricted data, etc).', max_length=1024, null=True, verbose_name='Additional Info'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='compute_env',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Compute Environment Format'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='compute_env_other',
            field=models.TextField(blank=True, default='', help_text='Details about the unlisted environment', max_length=1024, null=True, verbose_name='Other Environment Details'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, verbose_name='Does this submission contain GIS data and mapping?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='contents_proprietary',
            field=models.BooleanField(default=False, verbose_name='Does this submission contain restricted or proprietary data?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='contents_proprietary_sharing',
            field=models.BooleanField(default=False, verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='high_performance',
            field=models.BooleanField(default=False, verbose_name='Does this submission require a high-performance compute environment?'),
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='skip_edition',
            field=models.BooleanField(default=False, help_text='Is this manuscript being run without external Authors or Editors'),
        ),
        migrations.AddField(
            model_name='historicalsubmission',
            name='files_changed',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='historicalsubmission',
            name='launch_issues',
            field=models.TextField(blank=True, default='', help_text='Issues faced when attempting to launch the container', max_length=1024, null=True, verbose_name='Container Launch Issues'),
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='last_oauthproxy_forced_signin',
            field=models.DateTimeField(default=datetime.datetime(1900, 1, 1, 0, 0)),
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='wt_id',
            field=models.CharField(blank=True, max_length=24, null=True, verbose_name='User ID in Whole Tale'),
        ),
        migrations.AddField(
            model_name='historicalverificationmetadata',
            name='manuscript',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.manuscript'),
        ),
        migrations.AddField(
            model_name='historicalverificationmetadata',
            name='software_info',
            field=models.TextField(default='', help_text='Please provide the list of your used statistical software and their versions.', verbose_name='Statistical Software'),
        ),
        migrations.AddField(
            model_name='historicalverificationmetadataaudit',
            name='manuscript',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.manuscript'),
        ),
        migrations.AddField(
            model_name='historicalverificationmetadatabadge',
            name='manuscript',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.manuscript'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='additional_info',
            field=models.TextField(blank=True, default='', help_text='Additional info about the manuscript (e.g., approved exemptions, restricted data, etc).', max_length=1024, null=True, verbose_name='Additional Info'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='compute_env',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Compute Environment Format'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='compute_env_other',
            field=models.TextField(blank=True, default='', help_text='Details about the unlisted environment', max_length=1024, null=True, verbose_name='Other Environment Details'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, verbose_name='Does this submission contain GIS data and mapping?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='contents_proprietary',
            field=models.BooleanField(default=False, verbose_name='Does this submission contain restricted or proprietary data?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='contents_proprietary_sharing',
            field=models.BooleanField(default=False, verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='high_performance',
            field=models.BooleanField(default=False, verbose_name='Does this submission require a high-performance compute environment?'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='skip_edition',
            field=models.BooleanField(default=False, help_text='Is this manuscript being run without external Authors or Editors'),
        ),
        migrations.AddField(
            model_name='submission',
            name='files_changed',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='launch_issues',
            field=models.TextField(blank=True, default='', help_text='Issues faced when attempting to launch the container', max_length=1024, null=True, verbose_name='Container Launch Issues'),
        ),
        migrations.AddField(
            model_name='user',
            name='last_oauthproxy_forced_signin',
            field=models.DateTimeField(default=datetime.datetime(1900, 1, 1, 0, 0)),
        ),
        migrations.AddField(
            model_name='user',
            name='wt_id',
            field=models.CharField(blank=True, max_length=24, null=True, verbose_name='User ID in Whole Tale'),
        ),
        migrations.AddField(
            model_name='verificationmetadata',
            name='manuscript',
            field=models.OneToOneField(default=0, on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_vmetadata', to='main.manuscript'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='verificationmetadata',
            name='software_info',
            field=models.TextField(default='', help_text='Please provide the list of your used statistical software and their versions.', verbose_name='Statistical Software'),
        ),
        migrations.AddField(
            model_name='verificationmetadataaudit',
            name='manuscript',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, related_name='verificationmetadata_audits', to='main.manuscript'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='verificationmetadatabadge',
            name='manuscript',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, related_name='verificationmetadata_badges', to='main.manuscript'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='curation',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('incom_materials', 'Incomplete Materials'), ('major_issues', 'Major Issues'), ('minor_issues', 'Minor Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the curator', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='curation',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='datasource',
            name='text',
            field=models.CharField(default='', max_length=4000, verbose_name='Data Source'),
        ),
        migrations.AlterField(
            model_name='edition',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('issues', 'Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the editor', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='edition',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='gitfile',
            name='description',
            field=models.CharField(blank=True, default='', max_length=1024, null=True, verbose_name='file description'),
        ),
        migrations.AlterField(
            model_name='gitfile',
            name='tag',
            field=models.CharField(blank=True, choices=[('code', 'Code'), ('data', 'Data'), ('doc_readme', 'Documentation - Readme'), ('doc_codebook', 'Documentation - Codebook'), ('doc_other', 'Documentation - Other')], max_length=14, null=True, verbose_name='file type'),
        ),
        migrations.AlterField(
            model_name='historicalcuration',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('incom_materials', 'Incomplete Materials'), ('major_issues', 'Major Issues'), ('minor_issues', 'Minor Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the curator', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='historicalcuration',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='historicaledition',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('issues', 'Issues'), ('no_issues', 'No Issues')], default='new', help_text='Was the submission approved by the editor', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='historicaledition',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('awaiting_init', 'Awaiting Initial Submission'), ('awaiting_resub', 'Awaiting Author Resubmission'), ('reviewing', 'Editor Reviewing'), ('processing', 'Processing Submission'), ('completed', 'Completed')], default='new', help_text='The overall status of the manuscript in the review process', max_length=15, verbose_name='Manuscript Status'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contact_email',
            field=models.EmailField(help_text='Email address of the publication contact that will be stored in Dataverse', max_length=254, null=True, verbose_name='Corresponding Author Email Address'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contact_first_name',
            field=models.CharField(help_text='Given name of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Corresponding Author Given Name'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contact_last_name',
            field=models.CharField(help_text='Surname of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Corresponding Author Surname'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', max_length=1024, null=True, verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='pub_id',
            field=models.CharField(db_index=True, default='', help_text='The internal ID from the publication', max_length=200, verbose_name='Manuscript #'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qdr_review',
            field=models.BooleanField(blank=True, default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', null=True, verbose_name='QDR Review'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qual_analysis',
            field=models.BooleanField(blank=True, default=False, help_text='Whether this manuscript includes qualitative analysis', null=True, verbose_name='Qualitative Analysis'),
        ),
        migrations.AlterField(
            model_name='historicalnote',
            name='text',
            field=models.TextField(verbose_name='Note Text'),
        ),
        migrations.AlterField(
            model_name='historicalsubmission',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('in_progress_edition', 'In Progress Edition'), ('rejected_editor', 'Rejected Editor'), ('in_progress_curation', 'In Progress Curation'), ('in_progress_verification', 'In Progress Verification'), ('reviewed_awaiting_report', 'Reviewed Awaiting Report'), ('reviewed_awaiting_approve', 'Reviewed Report Awaiting Approval'), ('returned', 'Returned')], default='new', help_text='The status of the submission in the review process', max_length=25, verbose_name='Submission review status'),
        ),
        migrations.AlterField(
            model_name='historicalverification',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('not_attempted', 'Not Attempted'), ('minor_issues', 'Minor Issues'), ('major_issues', 'Major Issues'), ('success_w_mod', 'Success with Modification'), ('success', 'Success')], default='new', help_text='Was the submission able to be verified', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='historicalverification',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='historicalverificationmetadata',
            name='packages_info',
            field=models.TextField(default='', help_text='Please provide the list of your required packages and their versions.', verbose_name='Required Packages'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('awaiting_init', 'Awaiting Initial Submission'), ('awaiting_resub', 'Awaiting Author Resubmission'), ('reviewing', 'Editor Reviewing'), ('processing', 'Processing Submission'), ('completed', 'Completed')], default='new', help_text='The overall status of the manuscript in the review process', max_length=15, verbose_name='Manuscript Status'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contact_email',
            field=models.EmailField(help_text='Email address of the publication contact that will be stored in Dataverse', max_length=254, null=True, verbose_name='Corresponding Author Email Address'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contact_first_name',
            field=models.CharField(help_text='Given name of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Corresponding Author Given Name'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contact_last_name',
            field=models.CharField(help_text='Surname of the publication contact that will be stored in Dataverse', max_length=150, verbose_name='Corresponding Author Surname'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='description',
            field=models.TextField(blank=True, default='', help_text='The abstract for the manuscript', max_length=1024, null=True, verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='pub_id',
            field=models.CharField(db_index=True, default='', help_text='The internal ID from the publication', max_length=200, verbose_name='Manuscript #'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qdr_review',
            field=models.BooleanField(blank=True, default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', null=True, verbose_name='QDR Review'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qual_analysis',
            field=models.BooleanField(blank=True, default=False, help_text='Whether this manuscript includes qualitative analysis', null=True, verbose_name='Qualitative Analysis'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='get_display_name'),
        ),
        migrations.AlterField(
            model_name='note',
            name='text',
            field=models.TextField(verbose_name='Note Text'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', 'New'), ('in_progress_edition', 'In Progress Edition'), ('rejected_editor', 'Rejected Editor'), ('in_progress_curation', 'In Progress Curation'), ('in_progress_verification', 'In Progress Verification'), ('reviewed_awaiting_report', 'Reviewed Awaiting Report'), ('reviewed_awaiting_approve', 'Reviewed Report Awaiting Approval'), ('returned', 'Returned')], default='new', help_text='The status of the submission in the review process', max_length=25, verbose_name='Submission review status'),
        ),
        migrations.AlterField(
            model_name='verification',
            name='_status',
            field=django_fsm.FSMField(choices=[('new', '---'), ('not_attempted', 'Not Attempted'), ('minor_issues', 'Minor Issues'), ('major_issues', 'Major Issues'), ('success_w_mod', 'Success with Modification'), ('success', 'Success')], default='new', help_text='Was the submission able to be verified', max_length=15, verbose_name='Review'),
        ),
        migrations.AlterField(
            model_name='verification',
            name='report',
            field=models.TextField(default='', verbose_name='Details'),
        ),
        migrations.AlterField(
            model_name='verificationmetadata',
            name='packages_info',
            field=models.TextField(default='', help_text='Please provide the list of your required packages and their versions.', verbose_name='Required Packages'),
        ),
        migrations.DeleteModel(
            name='ContainerInfo',
        ),
        migrations.DeleteModel(
            name='HistoricalVerificationMetadataSoftware',
        ),
        migrations.DeleteModel(
            name='VerificationMetadataSoftware',
        ),
        migrations.AddField(
            model_name='localcontainerinfo',
            name='manuscript',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_localcontainerinfo', to='main.manuscript'),
        ),
        migrations.AddField(
            model_name='corereinvitation',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invite', to=settings.AUTH_USER_MODEL),
        ),
    ]