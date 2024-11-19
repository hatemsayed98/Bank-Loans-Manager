from datetime import datetime
from decimal import Decimal
import logging

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()


class BankBudget(models.Model):
    total_funds = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def available_funds(self):
        return self.total_funds

    def save(self, *args, **kwargs):
        if not self.pk and BankBudget.objects.exists():
            raise ValidationError("There can only be one BankBudget instance.")
        super().save(*args, **kwargs)

    def add_funds(self, amount):
        self.total_funds += Decimal(amount)
        self.save()

    @classmethod
    def get_instance(cls, for_update=False):
        if for_update:
            instance = cls.objects.select_for_update().get(pk=1)
        else:
            instance, created = cls.objects.get_or_create(pk=1)
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
    STATUS_PENDING_REVIEW = "pending_review"
    STATUS_PENDING_CUSTOMER = "pending_customer"
    STATUS_PENDING_APPROVAL = "pending_approval"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING_REVIEW, "Pending Review"),
        (STATUS_PENDING_APPROVAL, "Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_PENDING_CUSTOMER, "Pending Customer Input"),
    ]

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_REVIEW,
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE)
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

    def approve(self, approved_by):
        with transaction.atomic():
            bank_budget = BankBudget.objects.select_for_update().get(pk=1)

            loan_amount = Decimal(self.amount)
            total_funds = Decimal(bank_budget.total_funds)

            if total_funds < loan_amount:
                raise ValueError("Insufficient funds in bank budget.")

            bank_budget.total_funds -= loan_amount
            bank_budget.save()

            self.status = self.STATUS_APPROVED
            self.save()

            loan = Loan.objects.create(
                customer=self.customer,
                amount=loan_amount,
                term_months=self.final_duration_months,
                interest_rate=self.interest_rate,
                status=Loan.STATUS_IN_PROGRESS,
            )

            self.documents.update(loan=loan)

            logger.info(
                f"Loan request {self.id} approved by {approved_by.username}. "
                f"Loan amount: {loan_amount}. Bank total funds updated to {bank_budget.total_funds}."
            )

            return loan


class Loan(models.Model):
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FULLY_PAID = "fully_paid"
    STATUS_OVERDUE = "overdue"

    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_FULLY_PAID, "Fully Paid"),
        (STATUS_OVERDUE, "Overdue"),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    term_months = models.IntegerField(null=True, blank=True)
    interest_rate = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
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
            self.status = self.STATUS_FULLY_PAID
        elif self.has_deadline_passed():
            self.status = self.STATUS_OVERDUE
        else:
            self.status = self.STATUS_IN_PROGRESS
        self.save()


class LoanPayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
