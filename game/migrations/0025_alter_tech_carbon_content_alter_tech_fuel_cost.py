# Generated by Django 4.2.4 on 2023-11-01 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0024_alter_demand_cf_cf_pv_alter_demand_cf_cf_wind'),
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
