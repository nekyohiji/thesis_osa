from django.db import migrations

def backfill(apps, schema_editor):
    Log = apps.get_model('myapp', 'CommunityServiceLog')

    # Relax inconsistent legacy rows to a neutral state so the new CHECK will pass.
    Log.objects.filter(
        facilitator_source='admin', facilitator_user__isnull=True
    ).update(facilitator_source='')

    Log.objects.filter(
        facilitator_source='faculty', facilitator_faculty__isnull=True
    ).update(facilitator_source='')

    # If both FKs set, null the one that contradicts the source.
    Log.objects.filter(
        facilitator_source='admin',
        facilitator_user__isnull=False, facilitator_faculty__isnull=False
    ).update(facilitator_faculty=None)

    Log.objects.filter(
        facilitator_source='faculty',
        facilitator_faculty__isnull=False, facilitator_user__isnull=False
    ).update(facilitator_user=None)

    # Optional: align source if empty but exactly one FK is stamped.
    Log.objects.filter(
        facilitator_source='',
        facilitator_user__isnull=False, facilitator_faculty__isnull=True
    ).update(facilitator_source='admin')

    Log.objects.filter(
        facilitator_source='',
        facilitator_faculty__isnull=False, facilitator_user__isnull=True
    ).update(facilitator_source='faculty')

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0072_communityservicelog_facilitator_faculty_and_more'),
    ]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]