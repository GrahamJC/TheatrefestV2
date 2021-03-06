# Generated by Django 2.1.3 on 2018-11-22 11:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_auto_20181122_1126'),
    ]

    operations = [
        migrations.RenameField(
            model_name='refund',
            old_name='box_office',
            new_name='boxoffice',
        ),
        migrations.RenameField(
            model_name='sale',
            old_name='box_office',
            new_name='boxoffice',
        ),
        migrations.AlterField(
            model_name='boxoffice',
            name='festival',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='boxoffices', to='core.Festival'),
        ),
    ]
