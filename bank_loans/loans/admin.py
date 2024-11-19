from django.contrib import admin
from django.contrib.sites.models import Site

from .models import BankBudget
from .models import Document
from .models import Fund
from .models import Loan
from .models import LoanPayment
from .models import LoanRequest


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "amount",
        "term_months",
        "interest_rate",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("customer__username", "customer__email")
    readonly_fields = ("customer", "created_at", "updated_at")
    fieldsets = (
        (
            "Information",
            {
                "fields": (
                    "customer",
                    "amount",
                    "term_months",
                    "interest_rate",
                    "status",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ("loan", "amount_paid", "payment_date")
    list_filter = ("payment_date",)
    search_fields = ("loan__customer__username", "loan__customer__email")
    readonly_fields = (
        "loan",
        "amount_paid",
        "payment_date",
    )


@admin.register(BankBudget)
class BankBudgetAdmin(admin.ModelAdmin):
    list_display = ("total_funds",)


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = (
        "user",
        "amount",
        "created_at",
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "file", "loan_request", "loan", "created_at", "updated_at")
    search_fields = (
        "title",
        "loan_request__customer__username",
        "loan__customer__username",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "status",
        "amount",
        "secured",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = ("customer__username", "customer__email")
    readonly_fields = ("customer", "created_at", "updated_at")



admin.site.unregister(Site)
