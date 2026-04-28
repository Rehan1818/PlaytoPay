from rest_framework import serializers

from .models import Payout


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField(min_value=1)


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "merchant_id",
            "bank_account_id",
            "amount_paise",
            "status",
            "attempts",
            "created_at",
            "updated_at",
        ]
