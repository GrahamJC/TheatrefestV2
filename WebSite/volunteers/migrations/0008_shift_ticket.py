# Generated by Django 2.2.1 on 2019-06-20 08:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_auto_20190428_1653'),
        ('volunteers', '0007_shift_volunteer_can_accept'),
    ]

    operations = [
        migrations.AddField(
            model_name='shift',
            name='ticket',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='shift', to='tickets.Ticket'),
        ),
    ]