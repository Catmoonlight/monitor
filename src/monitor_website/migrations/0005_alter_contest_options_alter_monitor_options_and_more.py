# Generated by Django 4.0.5 on 2022-08-04 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_website', '0004_remove_monitor_allow_ghosts_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contest',
            options={'ordering': ['index']},
        ),
        migrations.AlterModelOptions(
            name='monitor',
            options={'ordering': ['index']},
        ),
        migrations.AlterModelOptions(
            name='problem',
            options={'ordering': ['index']},
        ),
        migrations.RemoveField(
            model_name='monitor',
            name='default_ghosts',
        ),
        migrations.AddField(
            model_name='contest',
            name='index',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='monitor',
            name='index',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='contest',
            name='cf_contest',
            field=models.CharField(max_length=20, verbose_name='Номер контеста'),
        ),
        migrations.AlterField(
            model_name='submit',
            name='index',
            field=models.CharField(max_length=20, verbose_name='Индекс'),
        ),
        migrations.AlterUniqueTogether(
            name='personality',
            unique_together={('monitor', 'nickname')},
        ),
    ]
