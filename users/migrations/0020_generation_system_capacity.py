# Generated by Django 4.2.4 on 2023-10-03 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0011_alter_tech_capacity'),
        ('users', '0019_remove_generation_system_capacity'),
    ]

    operations = [
        migrations.AddField(
            model_name='generation_system',
            name='capacity',
            field=models.ManyToManyField(related_name='generation_capacity_set', to='game.tech'),
        ),
    ]
