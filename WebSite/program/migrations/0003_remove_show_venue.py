# Generated by Django 4.2 on 2023-09-21 07:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0002_add_performance_venue'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='show',
            name='venue',
        ),
    ]