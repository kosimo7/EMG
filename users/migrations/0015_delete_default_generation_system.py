# Generated by Django 4.1.7 on 2023-03-14 11:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_rename_remaining_construction_until_constructed_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='default_generation_system',
        ),
    ]
