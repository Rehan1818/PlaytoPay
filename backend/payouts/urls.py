from django.urls import path

from .views import MerchantDashboardView, PayoutCreateView, PayoutHistoryView

urlpatterns = [
    path("payouts", PayoutCreateView.as_view(), name="payout-create"),
    path("payouts/history", PayoutHistoryView.as_view(), name="payout-history"),
    path("dashboard", MerchantDashboardView.as_view(), name="merchant-dashboard"),
]
