# Generated by Django 4.2.4 on 2023-10-18 11:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0013_games'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='games',
            new_name='sessions',
        ),
    ]