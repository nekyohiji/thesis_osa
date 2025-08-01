# Generated by Django 5.1.1 on 2025-07-19 12:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0017_lostandfound'),
    ]

    operations = [
        migrations.CreateModel(
            name='ViolationSettlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('settlement_type', models.CharField(choices=[('Apology Letter', 'Apology Letter'), ('Community Service', 'Community Service')], max_length=50)),
                ('is_settled', models.BooleanField(default=False)),
                ('settled_at', models.DateTimeField(blank=True, null=True)),
                ('violation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settlement', to='myapp.violation')),
            ],
            options={
                'db_table': 'violation_settlement',
            },
        ),
    ]
