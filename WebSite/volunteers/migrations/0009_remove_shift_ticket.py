# Generated by Django 2.2.1 on 2019-06-20 08:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('volunteers', '0008_shift_ticket'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shift',
            name='ticket',
        ),
    ]