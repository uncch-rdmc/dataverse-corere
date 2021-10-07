# Generated by Django 3.2.5 on 2021-09-28 21:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_auto_20210830_2217'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaleInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tale_id', models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Tale ID in Wholetale')),
                ('submission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='submission_taleinfo', to='main.submission')),
            ],
        ),
    ]