# Generated by Django 4.2.4 on 2023-09-29 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_alter_profile_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='budget',
            field=models.IntegerField(default=0),
        ),
    ]
