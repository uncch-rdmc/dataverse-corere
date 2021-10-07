# Generated by Django 3.2.5 on 2021-09-30 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0023_taleinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='taleinfo',
            name='binder_id',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Instance ID for container in Whole Tale'),
        ),
        migrations.AddField(
            model_name='taleinfo',
            name='binder_url',
            field=models.URLField(blank=True, default='', max_length=500, null=True, verbose_name='Binder URL'),
        ),
        migrations.AlterField(
            model_name='taleinfo',
            name='tale_id',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Tale ID in Whole Tale'),
        ),
    ]