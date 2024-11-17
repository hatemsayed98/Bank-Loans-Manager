from datetime import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()


class BankBudget(models.Model):
    total_funds = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def available_funds(self):
        return self.total_funds

    def save(self, *args, **kwargs):
        if not self.pk and BankBudget.objects.exists():
            raise ValidationError("There can only be one BankBudget instance.")
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        instance, created = cls.objects.get_or_create(id=1)
        return instance

    class Meta:
        verbose_name = "Bank Budget"
        verbose_name_plural = "Bank Budgets"


class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="funds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class Document(models.Model):
    file = models.FileField(upload_to="documents/")
    title = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    loan_request = models.ForeignKey(
        "LoanRequest",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    loan = models.ForeignKey(
        "Loan",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )


class LoanRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("pending_customer", "Awaiting Customer Input"),
        ("pending_approval", "Awaiting Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    interest_rate = models.FloatField(null=True, blank=True)
    max_duration_months = models.PositiveIntegerField()
    final_duration_months = models.PositiveIntegerField(null=True, blank=True)
    purpose = models.CharField(max_length=150)
    details = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    secured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_be_set_by_personnel(self):
        bank_budget = BankBudget.objects.first()
        if not bank_budget:
            return False, "Bank budget not defined."

        available_funds = bank_budget.available_funds()
        if self.max_amount and self.max_amount > available_funds:
            return (
                False,
                f"Maximum amount exceeds available bank funds ({available_funds:.2f}).",
            )

        return True, "Constraints can be set."

    def clean(self):
        if self.min_amount and self.max_amount and self.min_amount > self.max_amount:
            raise ValidationError("Minimum amount cannot exceed maximum amount.")
        if self.max_duration_months <= 0:
            raise ValidationError("Maximum duration must be greater than zero.")

    def approve(self):
        self.status = "approved"
        self.save()
        Loan.objects.create(
            customer=self.customer,
            amount=self.amount,
            term_months=self.final_duration_months,
            interest_rate=self.interest_rate,
            status="in_progress",
        )


class Loan(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("fully_paid", "Fully Paid"),
        ("overdue", "Overdue"),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    term_months = models.IntegerField(null=True, blank=True)
    interest_rate = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_progress",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_expected_payment(self):
        if self.interest_rate:
            interest_multiplier = Decimal(str(1 + Decimal(self.interest_rate) / 100))
            return self.amount * interest_multiplier
        return self.amount

    def total_paid(self):
        return sum(payment.amount_paid for payment in self.loanpayment_set.all())

    def is_fully_paid(self):
        return self.total_paid() >= self.total_expected_payment()

    def has_deadline_passed(self):
        if self.term_months:
            end_date = self.created_at + relativedelta(months=self.term_months)
            return datetime.now().date() > end_date.date()
        return False

    def update_status(self):
        if self.is_fully_paid():
            self.status = "fully_paid"
        elif self.has_deadline_passed():
            self.status = "overdue"
        self.save()


class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
