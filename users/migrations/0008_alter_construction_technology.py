# Generated by Django 4.1.7 on 2023-03-13 15:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0007_alter_tech_technology'),
        ('users', '0007_alter_generation_system_technology'),
    ]

    operations = [
        migrations.AlterField(
            model_name='construction',
            name='technology',
            field=models.ForeignKey(db_column='technology', on_delete=django.db.models.deletion.CASCADE, to='game.tech', to_field='technology'),
        ),
    ]
