# Generated by Django 3.2.13 on 2022-07-01 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_auto_20220601_2155"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataverseinstallation",
            name="url",
            field=models.URLField(help_text="Please include the protocol, but not the trailing slash.", verbose_name="URL"),
        ),
        migrations.AlterField(
            model_name="historicalmanuscript",
            name="packages_info",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Please provide the list of your required packages and their versions.",
                null=True,
                verbose_name="Required Packages",
            ),
        ),
        migrations.AlterField(
            model_name="historicalmanuscript",
            name="software_info",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Please provide the list of your used statistical software and their versions.",
                null=True,
                verbose_name="Statistical Software",
            ),
        ),
        migrations.AlterField(
            model_name="manuscript",
            name="packages_info",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Please provide the list of your required packages and their versions.",
                null=True,
                verbose_name="Required Packages",
            ),
        ),
        migrations.AlterField(
            model_name="manuscript",
            name="software_info",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Please provide the list of your used statistical software and their versions.",
                null=True,
                verbose_name="Statistical Software",
            ),
        ),
    ]