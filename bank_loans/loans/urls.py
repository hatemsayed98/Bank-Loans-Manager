from django.urls import path
from .api.views import (
    AcceptLoanRequestView,
    CustomerLoanListView,
    CustomerLoanRequestListView,
    CustomerSetLoanRequestSettingsView,
    FundProviderCreateView,
    FundProviderView,
    PersonnelLoanListView,
    PersonnelLoanRequestListView,
    CustomerLoanRequestCreateView,
    RejectLoanRequestView,
    SetLoanRequestSettingsView,
    RequestStatusView,
    LoanStatusView,
    LoanPaymentView,
)

app_name = "loans"

urlpatterns = [
    # Loan Providers
    path("funds/", FundProviderView.as_view(), name="fund-provider"),
    path(
        "funds/create/",
        FundProviderCreateView.as_view(),
        name="fund-provider-create",
    ),
    # Personnel Endpoints
    path(
        "personnel/requests/",
        PersonnelLoanRequestListView.as_view(),
        name="personnel-loan-requests",
    ),
    path("personnel/loans/", PersonnelLoanListView.as_view(), name="personnel-loans"),
    path(
        "personnel/requests/<int:pk>/set-settings/",
        SetLoanRequestSettingsView.as_view(),
        name="set-loan-request-settings",
    ),
    path(
        "personnel/requests/<int:pk>/accept/",
        AcceptLoanRequestView.as_view(),
        name="accept-loan-request",
    ),
    path(
        "personnel/requests/<int:pk>/reject/",
        RejectLoanRequestView.as_view(),
        name="reject-loan-request",
    ),
    # Customer Endpoints
    path(
        "customer/requests/",
        CustomerLoanRequestListView.as_view(),
        name="customer-loan-requests",
    ),
    path("customer/loans/", CustomerLoanListView.as_view(), name="customer-loans"),
    path(
        "customer/requests/create/",
        CustomerLoanRequestCreateView.as_view(),
        name="customer-loan-request-create",
    ),
    path(
        "customer/requests/<int:pk>/set-settings/",
        CustomerSetLoanRequestSettingsView.as_view(),
        name="customer-set-loan-request-settings",
    ),
    path(
        "customer/requests/<int:pk>/",
        RequestStatusView.as_view(),
        name="request-status",
    ),
    path("customer/loans/<int:pk>/", LoanStatusView.as_view(), name="loan-status"),
    path(
        "customer/loans/<int:pk>/pay/", LoanPaymentView.as_view(), name="loan-payment"
    ),
]
