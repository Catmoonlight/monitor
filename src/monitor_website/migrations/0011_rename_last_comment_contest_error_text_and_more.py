# Generated by Django 4.0.5 on 2022-08-06 06:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_website', '0010_submit_language_submit_max_time'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contest',
            old_name='last_comment',
            new_name='error_text',
        ),
        migrations.RemoveField(
            model_name='contest',
            name='status',
        ),
    ]