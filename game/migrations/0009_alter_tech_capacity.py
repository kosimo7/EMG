# Generated by Django 4.2.4 on 2023-10-03 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0008_tech_default_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tech',
            name='capacity',
            field=models.IntegerField(default=0),
        ),
    ]
