# Generated by Django 5.1.6 on 2025-03-06 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="provider",
            field=models.CharField(choices=[("LOCAL", "Local"), ("KAKAO", "Kakao")], default="LOCAL", max_length=10),
        ),
    ]
