# Generated by Django 5.1.1 on 2025-06-24 07:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_useraccount'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='useraccount',
            table='user_accounts',
        ),
    ]
