# Generated by Django 4.2.4 on 2023-10-23 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_profile_joined_game'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='ready',
            field=models.BooleanField(default=False),
        ),
    ]
