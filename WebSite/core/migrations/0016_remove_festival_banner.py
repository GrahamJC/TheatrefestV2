# Generated by Django 2.2 on 2019-04-27 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_festival_is_archived'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='festival',
            name='banner',
        ),
    ]