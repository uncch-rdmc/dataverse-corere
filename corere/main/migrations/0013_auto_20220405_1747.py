# Generated by Django 3.2.12 on 2022-04-05 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_auto_20220331_1612'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataverseinstallation',
            name='username',
            field=models.CharField(blank=True, default='', help_text='User that owns the API token. We store this only for informational purposes.', max_length=200, null=True, verbose_name='User Name'),
        ),
        migrations.AlterField(
            model_name='dataverseinstallation',
            name='name',
            field=models.CharField(max_length=200, verbose_name='Installation Name'),
        ),
    ]