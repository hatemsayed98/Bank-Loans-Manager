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


class FundSerializer(ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "user", "amount", "created_at"]
        read_only_fields = ["id", "created_at", "user"]

    def create(self, validated_data):
        user = self.context["request"].user
        fund = Fund.objects.create(user=user, **validated_data)

        bank_budget, _ = BankBudget.objects.get_or_create(id=1)
        bank_budget.total_funds += fund.amount
        bank_budget.save()

        return fund


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
        print("validated_data", validated_data.get("documents"))
        documents_data = validated_data.pop("documents", [])
        loan_request = LoanRequest.objects.create(**validated_data)

        print("documents_data", documents_data)
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
        loan_request = self.instance  # Access the instance being updated
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
    class Meta:
        model = Loan
        fields = [
            "id",
            "customer",
            "amount",
            "term_months",
            "interest_rate",
            "status",
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
        """Perform validation to ensure valid payment conditions."""
        loan = self.context["loan"]

        if loan.status == "fully_paid":
            raise serializers.ValidationError("This loan has already been fully paid.")

        remaining_balance = loan.total_expected_payment() - loan.total_paid()

        if attrs["amount_paid"] > remaining_balance:
            raise serializers.ValidationError(
                f"The amount exceeds the remaining balance of {remaining_balance:.2f}."
            )
        if attrs["amount_paid"] <= 0:
            raise serializers.ValidationError(
                "The payment amount must be greater than zero."
            )

        return attrs

    def create(self, validated_data):
        loan = self.context["loan"]
        payment = super().create(validated_data)
        loan.update_status()
        return payment
