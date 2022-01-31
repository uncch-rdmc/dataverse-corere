# Generated by Django 3.2.11 on 2022-01-25 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_auto_20220124_2024'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicalmanuscript',
            old_name='wt_compute_env_other',
            new_name='compute_env_other',
        ),
        migrations.RenameField(
            model_name='manuscript',
            old_name='wt_compute_env_other',
            new_name='compute_env_other',
        ),
        migrations.RemoveField(
            model_name='historicalmanuscript',
            name='wt_compute_env',
        ),
        migrations.RemoveField(
            model_name='manuscript',
            name='wt_compute_env',
        ),
        migrations.AddField(
            model_name='historicalmanuscript',
            name='compute_env',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Compute Environment Format'),
        ),
        migrations.AddField(
            model_name='manuscript',
            name='compute_env',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Compute Environment Format'),
        ),
    ]
