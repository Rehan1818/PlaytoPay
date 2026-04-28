from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LedgerEntry, Payout
from .serializers import PayoutCreateSerializer, PayoutSerializer
from .services import create_payout_request, ledger_balances


class PayoutCreateView(APIView):
    def post(self, request):
        merchant_id = int(request.headers.get("X-Merchant-Id", "1"))
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header required"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            response_body, status_code = create_payout_request(
                merchant_id=merchant_id,
                idempotency_key=idempotency_key,
                payload=serializer.validated_data,
            )
        except (ValueError, ValidationError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response_body, status=status_code)


class MerchantDashboardView(APIView):
    def get(self, request):
        merchant_id = int(request.query_params.get("merchant_id", "1"))
        balances = ledger_balances(merchant_id)
        recent_ledger = list(
            LedgerEntry.objects.filter(merchant_id=merchant_id)
            .order_by("-created_at")
            .values("id", "entry_type", "amount_paise", "note", "created_at")[:20]
        )
        payouts = Payout.objects.filter(merchant_id=merchant_id).order_by("-created_at")[:20]
        return Response(
            {
                "merchant_id": merchant_id,
                "balances": balances,
                "recent_ledger": recent_ledger,
                "payouts": PayoutSerializer(payouts, many=True).data,
            }
        )


class PayoutHistoryView(APIView):
    def get(self, request):
        merchant_id = int(request.query_params.get("merchant_id", "1"))
        limit = min(int(request.query_params.get("limit", "20")), 100)
        offset = max(int(request.query_params.get("offset", "0")), 0)
        queryset = Payout.objects.filter(merchant_id=merchant_id).order_by("-created_at")
        total_count = queryset.count()
        records = queryset[offset : offset + limit]
        return Response(
            {
                "merchant_id": merchant_id,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "results": PayoutSerializer(records, many=True).data,
            }
        )
