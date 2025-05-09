# Generated by Django 5.1.6 on 2025-03-05 07:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Terms",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=50)),
                ("detail", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("is_required", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Terms",
                "verbose_name_plural": "Terms",
                "db_table": "terms",
            },
        ),
        migrations.CreateModel(
            name="TermsAgreement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_agree", models.BooleanField(default=False)),
                ("terms", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="terms.terms")),
            ],
            options={
                "db_table": "terms_agreement",
            },
        ),
    ]
