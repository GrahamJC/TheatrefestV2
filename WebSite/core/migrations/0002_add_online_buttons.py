# Generated by Django 4.2 on 2024-03-01 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='buttons_issued',
            field=models.IntegerField(blank=True, default=0),
        ),
    ]