# Generated by Django 2.2.15 on 2020-11-09 22:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Keyword',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(default='', max_length=200, verbose_name='keyword')),
                ('manuscript', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_keywords', to='main.Manuscript')),
            ],
        ),
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(default='', max_length=200, verbose_name='data source')),
                ('manuscript', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_data_source', to='main.Manuscript')),
            ],
        ),
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(max_length=150, verbose_name='last name')),
                ('identifier_scheme', models.CharField(blank=True, choices=[('ORCID', 'ORCID'), ('ISNI', 'ISNI'), ('LCNA', 'LCNA'), ('VIAF', 'VIAF'), ('GND', 'GND'), ('DAI', 'DAI'), ('ResearcherID', 'ResearcherID'), ('ScopusID', 'ScopusID')], max_length=14, null=True, verbose_name='identifier scheme')),
                ('identifier', models.CharField(blank=True, max_length=150, null=True, verbose_name='identifier')),
                ('position', models.IntegerField(help_text='Position/order of the author in the list of authors', verbose_name='position')),
                ('manuscript', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manuscript_authors', to='main.Manuscript')),
            ],
        ),
    ]
