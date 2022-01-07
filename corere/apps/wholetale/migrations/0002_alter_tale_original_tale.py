# Generated by Django 3.2.5 on 2021-12-02 23:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wholetale', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tale',
            name='original_tale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tale_copies', to='wholetale.tale'),
        ),
    ]