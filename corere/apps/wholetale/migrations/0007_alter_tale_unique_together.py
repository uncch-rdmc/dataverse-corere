# Generated by Django 3.2.5 on 2021-12-17 18:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20211214_0034'),
        ('wholetale', '0006_alter_tale_group_connector'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='tale',
            unique_together={('submission', 'group_connector')},
        ),
    ]
