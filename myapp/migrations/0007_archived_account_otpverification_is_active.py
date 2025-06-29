# Generated by Django 5.1.1 on 2025-06-24 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_otpverification'),
    ]

    operations = [
        migrations.CreateModel(
            name='Archived_Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('otp', models.CharField(blank=True, max_length=6, null=True)),
                ('full_name', models.CharField(max_length=128)),
                ('role', models.CharField(max_length=20)),
                ('password', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'archive_account',
            },
        ),
        migrations.AddField(
            model_name='otpverification',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
