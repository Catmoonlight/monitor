# Generated by Django 4.0.5 on 2022-07-18 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_website', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='monitor',
            name='name',
        ),
        migrations.AlterField(
            model_name='personality',
            name='nickname',
            field=models.CharField(max_length=50),
        ),
    ]
