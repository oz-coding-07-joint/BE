# Generated by Django 5.1.6 on 2025-03-13 02:38

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("terms", "0003_termsagreement_deleted_at_termsagreement_restored_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="termsagreement",
            unique_together={("user", "terms")},
        ),
    ]
