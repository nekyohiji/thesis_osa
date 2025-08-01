# Generated by Django 5.1.1 on 2025-07-20 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0018_violationsettlement'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoodMoralRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('middle_name', models.CharField(blank=True, max_length=50)),
                ('surname', models.CharField(max_length=50)),
                ('ext', models.CharField(blank=True, max_length=10)),
                ('sex', models.CharField(max_length=10)),
                ('student_id', models.CharField(max_length=20)),
                ('program', models.CharField(max_length=100)),
                ('status', models.CharField(max_length=20)),
                ('date_graduated', models.DateField(blank=True, null=True)),
                ('inclusive_years', models.CharField(blank=True, max_length=20)),
                ('date_admission', models.DateField(blank=True, null=True)),
                ('purpose', models.CharField(max_length=100)),
                ('requester_name', models.CharField(max_length=100)),
                ('requester_email', models.EmailField(max_length=254)),
                ('requester_contact', models.CharField(max_length=20)),
                ('relationship', models.CharField(max_length=50)),
                ('upload_id', models.FileField(blank=True, null=True, upload_to='uploads/goodmoral/')),
                ('upload_ack_receipt', models.FileField(blank=True, null=True, upload_to='uploads/goodmoral/')),
                ('upload_diploma', models.FileField(blank=True, null=True, upload_to='uploads/goodmoral/')),
                ('is_approved', models.BooleanField(default=False)),
                ('is_rejected', models.BooleanField(default=False)),
                ('rejection_reason', models.TextField(blank=True)),
                ('is_paid', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'goodmoral',
            },
        ),
    ]
