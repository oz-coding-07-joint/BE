# Generated by Django 5.1.6 on 2025-03-20 08:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_instructor_user_alter_student_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="provider_id",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
