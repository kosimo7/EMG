# Generated by Django 4.2.4 on 2023-10-20 10:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0014_rename_games_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings',
            name='game',
            field=models.ForeignKey(default='Game1', on_delete=django.db.models.deletion.CASCADE, to='game.sessions', to_field='name'),
        ),
    ]
