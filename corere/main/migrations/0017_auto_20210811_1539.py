# Generated by Django 3.2.5 on 2021-08-11 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_auto_20210810_2200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasource',
            name='text',
            field=models.CharField(default='', max_length=4000, verbose_name='Data Source'),
        ),
        migrations.AlterField(
            model_name='historicalmanuscript',
            name='qdr_review',
            field=models.BooleanField(blank=True, default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', null=True, verbose_name='QDR Review'),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='qdr_review',
            field=models.BooleanField(blank=True, default=False, help_text='Does this manuscript need verification of qualitative results by QDR?', null=True, verbose_name='QDR Review'),
        ),
    ]
