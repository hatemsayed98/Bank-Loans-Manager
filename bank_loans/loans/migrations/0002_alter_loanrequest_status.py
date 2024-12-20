# Generated by Django 5.0.9 on 2024-11-18 14:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("loans", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loanrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_review", "Pending Review"),
                    ("pending_approval", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("pending_customer", "Pending Customer Input"),
                ],
                default="pending_review",
                max_length=50,
            ),
        ),
    ]
