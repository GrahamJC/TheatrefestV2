# Generated by Django 2.2 on 2019-05-04 09:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('volunteers', '0005_auto_20190218_0934'),
    ]

    operations = [
        migrations.AddField(
            model_name='shift',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
