# Generated by Django 4.2.4 on 2023-10-03 11:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_generation_system_capacity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generation_system',
            name='capacity',
        ),
    ]
