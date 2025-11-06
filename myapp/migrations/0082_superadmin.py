from django.db import migrations
from django.contrib.auth.hashers import make_password

EMAIL = "beverly.devega@tup.edu.ph"
FULL_NAME = "Adviser (Superadmin)"
ROLE = "superadmin"
RAW_PASSWORD = "DATINGQUEENSAOSA2025"  # rotate after use

def up(apps, schema_editor):
    UserAccount = apps.get_model("myapp", "UserAccount")
    UserAccount.objects.update_or_create(
        email=EMAIL,
        defaults={
            "full_name": FULL_NAME,
            "role": ROLE,
            "is_active": True,
            "password": make_password(RAW_PASSWORD),
            "must_change_password": True,
        },
    )

def down(apps, schema_editor):
    UserAccount = apps.get_model("myapp", "UserAccount")
    UserAccount.objects.filter(email=EMAIL).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0081_alter_useraccount_role"),  # or whatever your latest is
    ]
    operations = [
        migrations.RunPython(up, reverse_code=down),
    ]
