# Generated by Django 4.2.4 on 2023-11-15 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0030_alter_backup_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='backup',
            name='round',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
