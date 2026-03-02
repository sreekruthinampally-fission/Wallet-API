from decimal import Decimal


def create_user(client, email="user1@example.com"):
    response = client.post("/users", json={"email": email})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_wallet(client):
    user_id = create_user(client)
    response = client.post(f"/wallets/{user_id}")
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == user_id
    assert Decimal(body["balance"]) == Decimal("0.00")


def test_credit_updates_balance_and_ledger(client):
    user_id = create_user(client)
    client.post(f"/wallets/{user_id}")
    credit = client.post(f"/wallets/{user_id}/credit", json={"amount": "50.00", "reference": "salary"})
    assert credit.status_code == 200
    assert Decimal(credit.json()["balance"]) == Decimal("50.00")

    ledger = client.get(f"/wallets/{user_id}/ledger")
    assert ledger.status_code == 200
    items = ledger.json()["items"]
    assert len(items) == 1
    assert items[0]["entry_type"] == "credit"
    assert Decimal(items[0]["amount"]) == Decimal("50.00")
    assert Decimal(items[0]["balance_after"]) == Decimal("50.00")


def test_debit_success(client):
    user_id = create_user(client)
    client.post(f"/wallets/{user_id}")
    client.post(f"/wallets/{user_id}/credit", json={"amount": "100.00"})
    debit = client.post(f"/wallets/{user_id}/debit", json={"amount": "40.00"})
    assert debit.status_code == 200
    assert Decimal(debit.json()["balance"]) == Decimal("60.00")

    balance = client.get(f"/wallets/{user_id}/balance")
    assert balance.status_code == 200
    assert Decimal(balance.json()["balance"]) == Decimal("60.00")


def test_debit_insufficient_funds_has_no_ledger_row(client):
    user_id = create_user(client)
    client.post(f"/wallets/{user_id}")
    client.post(f"/wallets/{user_id}/credit", json={"amount": "20.00"})
    failed = client.post(f"/wallets/{user_id}/debit", json={"amount": "50.00"})
    assert failed.status_code == 409

    ledger = client.get(f"/wallets/{user_id}/ledger")
    items = ledger.json()["items"]
    assert len(items) == 1
    assert items[0]["entry_type"] == "credit"


def test_ledger_pagination(client):
    user_id = create_user(client)
    client.post(f"/wallets/{user_id}")
    for value in ["10.00", "20.00", "30.00"]:
        client.post(f"/wallets/{user_id}/credit", json={"amount": value})

    first_page = client.get(f"/wallets/{user_id}/ledger?limit=2&offset=0")
    second_page = client.get(f"/wallets/{user_id}/ledger?limit=2&offset=2")
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()["items"]) == 2
    assert len(second_page.json()["items"]) == 1


def test_create_wallet_for_missing_user_fails(client):
    response = client.post("/wallets/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
