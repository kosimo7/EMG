# Generated by Django 4.1.7 on 2023-03-07 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0002_tech_carbon_content_tech_fixed_cost_tech_fuel_cost'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tech',
            name='carbon_content',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name='tech',
            name='fuel_cost',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]