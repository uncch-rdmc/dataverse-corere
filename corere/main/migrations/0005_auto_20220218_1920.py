# Generated by Django 3.2.12 on 2022-02-18 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_auto_20220217_1613'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='contents_proprietary',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='high_performance',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript require a high-performance compute environment?'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qdr_review',
            field=models.BooleanField(default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', verbose_name='QDR Review'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qual_analysis',
            field=models.BooleanField(default=False, help_text='Whether this manuscript includes qualitative analysis', verbose_name='Qualitative Analysis'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contents_gis',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript contain GIS data and mapping?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='contents_proprietary',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript contain restricted or proprietary data?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='high_performance',
            field=models.BooleanField(default=False, verbose_name='Does this manuscript require a high-performance compute environment?'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qdr_review',
            field=models.BooleanField(default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', verbose_name='QDR Review'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qual_analysis',
            field=models.BooleanField(default=False, help_text='Whether this manuscript includes qualitative analysis', verbose_name='Qualitative Analysis'),
        ),
    ]
