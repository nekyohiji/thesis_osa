from django.db import migrations
from django.utils.timezone import now

def create_default_admin(apps, schema_editor):
    UserAccount = apps.get_model('myapp', 'UserAccount')

    # Only create admin if none exists
    if not UserAccount.objects.filter(role='admin').exists():
        from django.contrib.auth.hashers import make_password
        UserAccount.objects.create(
            full_name='OSA Head',
            email='jxhotel0@gmail.com',
            password=make_password('osahead25'),  # You can change this
            role='admin',
            is_active=True,
            created_at=now()
        )

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0007_archived_account_otpverification_is_active'),
    ]

    operations = [
        migrations.RunPython(create_default_admin),
    ]