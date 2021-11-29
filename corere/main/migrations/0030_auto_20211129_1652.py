# Generated by Django 3.2.5 on 2021-11-29 16:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_auto_20211115_2204'),
    ]

    operations = [
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
                ('manuscript', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_localcontainerinfo', to='main.manuscript')),
            ],
        ),
        migrations.DeleteModel(
            name='ContainerInfo',
        ),
    ]
