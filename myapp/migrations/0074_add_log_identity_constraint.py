from django.db import migrations, models
from django.db.models import Q

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0073_backfill_log_identity'),
    ]
    operations = [
        migrations.AddConstraint(
            model_name='communityservicelog',
            constraint=models.CheckConstraint(
                name='log_identity_consistent',
                check=(
                    Q(facilitator_source='admin',
                      facilitator_user__isnull=False,
                      facilitator_faculty__isnull=True)
                    |
                    Q(facilitator_source='faculty',
                      facilitator_faculty__isnull=False,
                      facilitator_user__isnull=True)
                    |
                    Q(facilitator_source='',
                      facilitator_user__isnull=True,
                      facilitator_faculty__isnull=True)
                ),
            ),
        ),
    ]
