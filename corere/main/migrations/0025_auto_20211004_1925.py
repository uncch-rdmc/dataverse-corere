# Generated by Django 3.2.5 on 2021-10-04 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_auto_20210930_1642'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmanuscript',
            name='wt_compute_env',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Whole Tale Compute Environment Format'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='wt_compute_env',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Whole Tale Compute Environment Format'),
        ),
    ]
