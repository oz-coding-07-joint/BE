# Generated by Django 5.1.6 on 2025-03-21 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_provider_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="instructor",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="instructor",
            name="restored_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="instructor",
            name="transaction_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="student",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="student",
            name="restored_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="student",
            name="transaction_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="provider_id",
            field=models.CharField(max_length=20, null=True),
        ),
    ]
