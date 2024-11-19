import logging
from django.db import transaction
from decimal import Decimal
from rest_framework.serializers import ModelSerializer
from bank_loans.loans.models import (
    BankBudget,
    Document,
    Fund,
    Loan,
    LoanPayment,
    LoanRequest,
)
from rest_framework import serializers

logger = logging.getLogger(__name__)


class FundSerializer(ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "user", "amount", "created_at"]
        read_only_fields = ["id", "created_at", "user"]

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        fund = Fund.objects.create(user=user, **validated_data)

        success = self.send_funds_to_bank(fund.amount, user)
        if not success:
            raise Exception("Failed to send funds to the bank.")

        bank_budget, _ = BankBudget.objects.get_or_create(id=1)
        bank_budget.add_funds(fund.amount)
        bank_budget.save()

        return fund

    def send_funds_to_bank(self, fund_amount, user):
        print(
            f"Simulating sending {fund_amount} funds from provider {user.username} to the bank."
        )
        return True


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file", "title", "details", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_file(self, value):
        allowed_extensions = [
            "pdf",
            "doc",
            "docx",
            "odt",
            "jpg",
            "jpeg",
            "png",
            "gif",
            "bmp",
            "tiff",
        ]
        ext = value.name.split(".")[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(allowed_extensions)}"
            )
        return value


class LoanRequestSerializer(serializers.ModelSerializer):
    secured = serializers.BooleanField(required=True)
    documents = DocumentSerializer(many=True, required=False)

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "customer",
            "status",
            "min_amount",
            "max_amount",
            "interest_rate",
            "max_duration_months",
            "final_duration_months",
            "purpose",
            "details",
            "documents",
            "amount",
            "secured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer", "status", "created_at", "updated_at"]

    def create(self, validated_data):
        documents_data = validated_data.pop("documents", [])
        loan_request = LoanRequest.objects.create(**validated_data)

        for document_data in documents_data:
            Document.objects.create(loan_request=loan_request, **document_data)

        return loan_request


class LoanRequestSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRequest
        fields = [
            "min_amount",
            "max_amount",
            "interest_rate",
            "max_duration_months",
        ]

    def validate(self, data):
        min_amount = data.get("min_amount")
        max_amount = data.get("max_amount")

        if (
            min_amount is not None
            and max_amount is not None
            and min_amount > max_amount
        ):
            raise serializers.ValidationError(
                "Maximum amount must be greater than or equal to the minimum amount."
            )

        return data


class CustomerLoanRequestSettingsSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    final_duration_months = serializers.IntegerField(required=True)

    class Meta:
        model = LoanRequest
        fields = ["amount", "final_duration_months"]

    def validate_final_duration_months(self, value):
        if value <= 0:
            raise serializers.ValidationError("Final duration months must be positive.")
        loan_request = self.instance
        if value > loan_request.max_duration_months:
            raise serializers.ValidationError(
                f"Final duration months cannot exceed the maximum allowed duration of {loan_request.max_duration_months} months."
            )
        return value

    def validate_amount(self, value):
        if value is None:
            raise serializers.ValidationError("Amount cannot be None.")
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


class LoanSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, required=False)

    class Meta:
        model = Loan
        fields = [
            "id",
            "customer",
            "amount",
            "term_months",
            "interest_rate",
            "status",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer", "status", "created_at", "updated_at"]

    def create(self, validated_data):
        customer = self.context["request"].user
        return Loan.objects.create(
            customer=customer, status="pending", **validated_data
        )


class LoanPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPayment
        fields = ["id", "loan", "amount_paid", "payment_date"]
        read_only_fields = ["id", "loan", "payment_date"]

    def validate(self, attrs):
        loan = self.context["loan"]

        if loan.status == Loan.STATUS_FULLY_PAID:
            raise serializers.ValidationError("This loan has already been fully paid.")

        remaining_balance = Decimal(loan.total_expected_payment()) - Decimal(
            loan.total_paid()
        )

        if Decimal(attrs["amount_paid"]) > remaining_balance:
            raise serializers.ValidationError(
                f"The amount exceeds the remaining balance of {remaining_balance:.2f}."
            )
        if Decimal(attrs["amount_paid"]) <= 0:
            raise serializers.ValidationError(
                "The payment amount must be greater than zero."
            )

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            loan = self.context["loan"]

            success = self.simulate_fund_transfer(validated_data["amount_paid"], loan)
            if not success:
                raise serializers.ValidationError("Fund transfer failed.")

            payment = super().create(validated_data)
            loan.update_status()

            bank_budget = BankBudget.get_instance(for_update=True)
            bank_budget.add_funds(payment.amount_paid)
            bank_budget.save()

            logger.info(
                f"User {self.context['request'].user} made a payment of {payment.amount_paid} "
                f"on loan {loan.id}. Bank total funds updated to {bank_budget.total_funds}."
            )

        return payment

    def simulate_fund_transfer(self, amount, loan):
        """
        Simulate the process of transferring funds. This function can be replaced with
        actual integration to an external payment service.
        """
        print(f"Simulating transfer of {amount} for loan ID {loan.id}.")
        return True
