# Generated by Django 4.1.7 on 2023-03-07 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tech',
            name='carbon_content',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tech',
            name='fixed_cost',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='tech',
            name='fuel_cost',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
