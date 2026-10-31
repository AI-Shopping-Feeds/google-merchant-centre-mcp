"""Order Tracking sub-API (Merchant API v1): send order tracking signals so Google
can show accurate shipping speeds and earn you the fast/free shipping badges."""

from __future__ import annotations

from typing import Any

from ..client import MerchantClient


def register(mcp, client: MerchantClient) -> None:
    acct = client.account_path()

    @mcp.tool()
    def gmc_create_order_tracking_signal(
        signal: dict[str, Any], order_tracking_signal_id: str | None = None
    ) -> dict[str, Any]:
        """Create an order tracking signal for one order.

        signal example:
            {
              "orderId": "ORDER-123",
              "orderCreatedTime": {"year": 2026, "month": 10, "day": 30, "hours": 9,
                                   "timeZone": {"id": "America/New_York"}},
              "deliveryPostalCode": "10001",
              "deliveryRegionCode": "US",
              "customerShippingFee": {"amountMicros": "0", "currencyCode": "USD"},
              "lineItems": [{"lineItemId": "1", "productId": "online:en:US:SKU1",
                             "quantity": "1"}],
              "shippingInfo": [{"shipmentId": "S1", "carrier": "UPS",
                                "trackingId": "1Z...", "shippingStatus": "SHIPPED",
                                "originPostalCode": "07001", "originRegionCode": "US",
                                "shippedTime": {...}}],
              "shipmentLineItemMapping": [{"shipmentId": "S1", "lineItemId": "1",
                                           "quantity": "1"}]
            }
        Set signal["merchantId"] when sending on behalf of a sub-account.
        order_tracking_signal_id: optional ID to assign to the signal.
        Signals can't be read back, updated or deleted through the API.
        """
        params = (
            {"orderTrackingSignalId": order_tracking_signal_id}
            if order_tracking_signal_id
            else None
        )
        return client.request(
            "POST",
            f"ordertracking/v1/{acct}/orderTrackingSignals",
            params=params,
            json_body=signal,
            op="create_order_tracking_signal",
        )
