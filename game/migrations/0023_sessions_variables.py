# Generated by Django 4.2.4 on 2023-10-26 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0022_demand_cf_unique_set'),
    ]

    operations = [
        migrations.AddField(
            model_name='sessions',
            name='variables',
            field=models.CharField(default='game_variables', max_length=30),
        ),
    ]