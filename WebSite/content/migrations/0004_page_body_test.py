# Generated by Django 2.1.5 on 2019-02-17 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0003_auto_20190217_0921'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='body_test',
            field=models.TextField(blank=True, default=''),
        ),
    ]
