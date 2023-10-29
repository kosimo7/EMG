# Generated by Django 4.2.4 on 2023-10-20 11:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0015_settings_game'),
    ]

    operations = [
        migrations.AlterField(
            model_name='settings',
            name='game',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='game.sessions', to_field='name'),
        ),
        migrations.AlterField(
            model_name='settings',
            name='name',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterUniqueTogether(
            name='settings',
            unique_together={('name', 'game')},
        ),
    ]