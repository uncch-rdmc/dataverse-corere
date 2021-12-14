# Generated by Django 3.2.5 on 2021-12-14 00:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20211130_0115'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaluser',
            name='invite_key',
        ),
        migrations.RemoveField(
            model_name='user',
            name='invite_key',
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='invite',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='main.corereinvitation'),
        ),
        migrations.AddField(
            model_name='user',
            name='invite',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.corereinvitation'),
        ),
    ]
