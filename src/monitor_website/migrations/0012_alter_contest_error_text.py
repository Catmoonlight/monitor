# Generated by Django 4.0.5 on 2022-08-06 06:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_website', '0011_rename_last_comment_contest_error_text_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='error_text',
            field=models.TextField(null=True),
        ),
    ]