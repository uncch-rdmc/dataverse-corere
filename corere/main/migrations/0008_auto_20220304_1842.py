# Generated by Django 3.2.12 on 2022-03-04 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_auto_20220226_1542'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_restricted',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_restricted_sharing',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
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
            model_name='manuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contents_restricted',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contents_restricted_sharing',
            field=models.BooleanField(default=False, help_text='TODO', verbose_name='Are you restricted from sharing this data with Odum for verification only?'),
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
    ]