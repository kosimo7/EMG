# Generated by Django 4.1.7 on 2023-03-14 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_remove_generation_system_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='default_generation_system',
            name='amount',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
