import logging
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend

from bank_loans.loans.models import BankBudget, Fund, Loan, LoanRequest
from bank_loans.loans.permissions import IsProvider, IsCustomer, IsBankPersonnel
from .serializers import (
    CustomerLoanRequestSettingsSerializer,
    DocumentSerializer,
    FundSerializer,
    LoanRequestSerializer,
    LoanRequestSettingsSerializer,
    LoanSerializer,
    LoanPaymentSerializer,
)


logger = logging.getLogger(__name__)


# Funds
class FundProviderView(generics.ListAPIView):
    queryset = Fund.objects.all()
    serializer_class = FundSerializer
    permission_classes = [IsAuthenticated, IsProvider]

    def get_queryset(self):
        return Fund.objects.filter(user=self.request.user)


class FundProviderCreateView(generics.CreateAPIView):
    queryset = Fund.objects.all()
    serializer_class = FundSerializer
    permission_classes = [IsAuthenticated, IsProvider]

    def perform_create(self, serializer):
        serializer.save()


# Personall
class PersonnelLoanRequestListView(generics.ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated, IsBankPersonnel]
    queryset = LoanRequest.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "updated_at"]


class PersonnelLoanListView(generics.ListAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated, IsBankPersonnel]
    queryset = Loan.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "updated_at"]


class SetLoanRequestSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsBankPersonnel]

    def post(self, request, pk):
        try:
            loan_request = LoanRequest.objects.get(
                pk=pk, status=LoanRequest.STATUS_PENDING_REVIEW
            )
        except LoanRequest.DoesNotExist:
            return Response(
                {"detail": "Loan request not found or not pending."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LoanRequestSettingsSerializer(
            loan_request, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        max_amount = serializer.validated_data.get("max_amount")
        bank_budget = BankBudget.objects.first()
        if not bank_budget or (
            max_amount and max_amount > bank_budget.available_funds()
        ):
            return Response(
                {"detail": "Maximum amount exceeds available bank funds."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(status=LoanRequest.STATUS_PENDING_CUSTOMER)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcceptLoanRequestView(APIView):
    permission_classes = [IsAuthenticated, IsBankPersonnel]

    def post(self, request, pk):
        try:
            loan_request = LoanRequest.objects.get(
                pk=pk, status=LoanRequest.STATUS_PENDING_APPROVAL
            )
        except LoanRequest.DoesNotExist:
            return Response(
                {"detail": "Loan request not found or not pending approval."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            loan_request.approve(request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "detail": "Loan request approved, loan created, and documents transferred."
            },
            status=status.HTTP_200_OK,
        )


class RejectLoanRequestView(APIView):
    permission_classes = [IsAuthenticated, IsBankPersonnel]

    def post(self, request, pk):
        with transaction.atomic():
            try:
                loan_request = LoanRequest.objects.select_for_update().get(pk=pk)
            except LoanRequest.DoesNotExist:
                return Response(
                    {"detail": "Loan request not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if loan_request.status in [
                LoanRequest.STATUS_APPROVED,
                LoanRequest.STATUS_REJECTED,
            ]:
                return Response(
                    {"detail": f"Loan request has already been {loan_request.status}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            loan_request.status = LoanRequest.STATUS_REJECTED
            loan_request.save()

        return Response({"detail": "Loan request rejected."}, status=status.HTTP_200_OK)


# Customer
class CustomerLoanRequestListView(generics.ListAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "updated_at"]

    def get_queryset(self):
        return LoanRequest.objects.filter(customer=self.request.user)


class CustomerLoanListView(generics.ListAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["created_at", "updated_at"]

    def get_queryset(self):
        return Loan.objects.filter(customer=self.request.user)


class CustomerLoanRequestCreateView(generics.CreateAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated, IsCustomer]


class CustomerLoanRequestCreateView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request, *args, **kwargs):

        serializer = LoanRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        loan_request = LoanRequest.objects.create(
            customer=request.user,
            max_duration_months=validated_data.get("max_duration_months"),
            final_duration_months=validated_data.get("final_duration_months"),
            purpose=validated_data.get("purpose"),
            details=validated_data.get("details"),
            amount=validated_data.get("amount"),
            secured=validated_data.get("secured"),
        )

        documents = request.FILES.getlist("documents")
        for document in documents:
            document_data = {
                "file": document,
                "title": document.name,
                "loan_request": loan_request.id,
            }
            document_serializer = DocumentSerializer(data=document_data)
            document_serializer.is_valid(raise_exception=True)
            document_serializer.save(loan_request=loan_request)

        return Response(
            LoanRequestSerializer(loan_request).data, status=status.HTTP_201_CREATED
        )


class CustomerSetLoanRequestSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request, pk):
        try:
            loan_request = LoanRequest.objects.get(
                pk=pk, customer=request.user, status=LoanRequest.STATUS_PENDING_CUSTOMER
            )
        except LoanRequest.DoesNotExist:
            return Response(
                {"detail": "Loan request not found or not awaiting customer input."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerLoanRequestSettingsSerializer(
            loan_request, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data.get("amount")
        if amount < loan_request.min_amount or amount > loan_request.max_amount:
            return Response(
                {
                    "detail": "Amount must be within the range set by the bank personnel."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bank_budget = BankBudget.objects.first()
        if bank_budget and amount > bank_budget.available_funds():
            return Response(
                {"detail": "Insufficient bank funds."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        loan_request.status = LoanRequest.STATUS_PENDING_APPROVAL
        loan_request.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestStatusView(generics.RetrieveAPIView):
    serializer_class = LoanRequestSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return LoanRequest.objects.filter(customer=self.request.user)


class LoanStatusView(generics.RetrieveAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Loan.objects.filter(customer=self.request.user)


class LoanPaymentView(generics.CreateAPIView):
    serializer_class = LoanPaymentSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        loan_id = self.kwargs.get("pk")
        try:
            loan = Loan.objects.get(pk=loan_id)
        except Loan.DoesNotExist:
            raise NotFound("The specified loan does not exist.")

        if loan.customer != self.request.user:
            raise PermissionDenied(
                "You are not authorized to make payments for this loan."
            )

        context["loan"] = loan
        return context

    def perform_create(self, serializer):
        loan = self.get_serializer_context().get("loan")
        serializer.save(loan=loan)
