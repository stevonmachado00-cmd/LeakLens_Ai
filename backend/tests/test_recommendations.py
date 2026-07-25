from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.statement import Subscription, BillingCycle, SubscriptionStatus
from app.models.user import User


def register_and_get_user(client, *, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Rec User", "email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Find user id via /auth/me
    me = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, me


def test_duplicate_detection(client, db_session):
    headers, me = register_and_get_user(client, email="dup@example.com")
    user_id = me["id"]

    sub1 = Subscription(
        user_id=user_id,
        merchant="StreamOne",
        normalized_merchant="streamone",
        billing_cycle=BillingCycle.MONTHLY,
        average_amount=Decimal("9.99"),
        last_charge_date=datetime.now(timezone.utc),
        confidence=Decimal("0.9"),
        status=SubscriptionStatus.DETECTED,
    )
    sub2 = Subscription(
        user_id=user_id,
        merchant="Stream One",
        normalized_merchant="streamone",
        billing_cycle=BillingCycle.YEARLY,
        average_amount=Decimal("5.99"),
        last_charge_date=datetime.now(timezone.utc),
        confidence=Decimal("0.8"),
        status=SubscriptionStatus.DETECTED,
    )
    db_session.add_all([sub1, sub2])
    db_session.commit()

    resp = client.get("/api/v1/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()
    assert any(r["recommendation_type"] == "duplicate" for r in recs)


def test_high_cost_detection(client, db_session):
    headers, me = register_and_get_user(client, email="highcost@example.com")
    user_id = me["id"]

    # two cheap subs and one expensive
    subs = [
        Subscription(
            user_id=user_id,
            merchant="Service A",
            normalized_merchant="servicea",
            billing_cycle=BillingCycle.MONTHLY,
            average_amount=Decimal("5.00"),
            last_charge_date=datetime.now(timezone.utc),
            confidence=Decimal("0.9"),
            status=SubscriptionStatus.DETECTED,
        ),
        Subscription(
            user_id=user_id,
            merchant="Service B",
            normalized_merchant="serviceb",
            billing_cycle=BillingCycle.MONTHLY,
            average_amount=Decimal("6.00"),
            last_charge_date=datetime.now(timezone.utc),
            confidence=Decimal("0.9"),
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

    resp = client.get("/api/v1/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()
    assert any(r["recommendation_type"] == "high_cost" for r in recs)


def test_generate_endpoint_returns_same(client, db_session):
    headers, me = register_and_get_user(client, email="regen@example.com")
    user_id = me["id"]

    sub = Subscription(
        user_id=user_id,
        merchant="Annualizable",
        normalized_merchant="annualizable",
        billing_cycle=BillingCycle.MONTHLY,
        average_amount=Decimal("10.00"),
        last_charge_date=datetime.now(timezone.utc),
        confidence=Decimal("0.9"),
        status=SubscriptionStatus.DETECTED,
    )
    db_session.add(sub)
    db_session.commit()

    get_resp = client.get("/api/v1/recommendations", headers=headers)
    post_resp = client.post("/api/v1/recommendations/generate", headers=headers)
    assert get_resp.status_code == 200
    assert post_resp.status_code == 200
    assert get_resp.json() == post_resp.json()
