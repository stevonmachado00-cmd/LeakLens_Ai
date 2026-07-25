from decimal import Decimal
from datetime import datetime, timezone

from app.models.statement import Subscription, BillingCycle, SubscriptionStatus


def register_and_get_user(client, *, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Score User", "email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"******"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, me


def test_score_basic(client, db_session):
    headers, me = register_and_get_user(client, email="score_basic@example.com")
    user_id = me["id"]

    # Add one inexpensive subscription
    sub = Subscription(
        user_id=user_id,
        merchant="SmallService",
        normalized_merchant="smallservice",
        billing_cycle=BillingCycle.MONTHLY,
        average_amount=Decimal("5.00"),
        last_charge_date=datetime.now(timezone.utc),
        confidence=Decimal("0.9"),
        status=SubscriptionStatus.DETECTED,
    )
    db_session.add(sub)
    db_session.commit()

    resp = client.get("/api/v1/leak-score", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert body["active_subscriptions"] == 1
    assert body["monthly_spend"] == "5.00"


def test_score_with_duplicates_and_high_cost(client, db_session):
    headers, me = register_and_get_user(client, email="score_dup@example.com")
    user_id = me["id"]

    subs = [
        Subscription(
            user_id=user_id,
            merchant="StreamOne",
            normalized_merchant="streamone",
            billing_cycle=BillingCycle.MONTHLY,
            average_amount=Decimal("9.99"),
            last_charge_date=datetime.now(timezone.utc),
            confidence=Decimal("0.9"),
            status=SubscriptionStatus.DETECTED,
        ),
        Subscription(
            user_id=user_id,
            merchant="Stream One",
            normalized_merchant="streamone",
            billing_cycle=BillingCycle.YEARLY,
            average_amount=Decimal("5.99"),
            last_charge_date=datetime.now(timezone.utc),
            confidence=Decimal("0.8"),
            status=SubscriptionStatus.DETECTED,
        ),
        Subscription(
            user_id=user_id,
            merchant="Premium Service",
            normalized_merchant="premiumservice",
            billing_cycle=BillingCycle.MONTHLY,
            average_amount=Decimal("30.00"),
            last_charge_date=datetime.now(timezone.utc),
            confidence=Decimal("0.9"),
            status=SubscriptionStatus.DETECTED,
        ),
    ]
    db_session.add_all(subs)
    db_session.commit()

    resp = client.get("/api/v1/leak-score", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_subscriptions"] == 3
    # Expect duplicate count to be at least 1
    assert body["duplicate_subscriptions"] >= 1
    # Expect high cost detected
    assert body["high_cost_subscriptions"] >= 1

