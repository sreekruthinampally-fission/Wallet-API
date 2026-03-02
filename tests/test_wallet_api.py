from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.services.wallet_service import InsufficientFundsError, WalletService


def create_user(client, email: str = "user1@example.com") -> str:
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


def test_credit_rejects_more_than_two_decimal_places(client):
    user_id = create_user(client, "precision@example.com")
    client.post(f"/wallets/{user_id}")
    response = client.post(f"/wallets/{user_id}/credit", json={"amount": "10.999"})
    assert response.status_code == 422


def test_wallet_routes_require_valid_uuid(client):
    response = client.post("/wallets/not-a-uuid")
    assert response.status_code == 422


def test_concurrent_debits_are_consistent(client):
    user_id = create_user(client, "concurrency@example.com")
    create_wallet_response = client.post(f"/wallets/{user_id}")
    assert create_wallet_response.status_code == 201
    seed_credit = client.post(f"/wallets/{user_id}/credit", json={"amount": "100.00"})
    assert seed_credit.status_code == 200

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    def debit_once() -> tuple[bool, str | None]:
        db = SessionLocal()
        try:
            WalletService.debit(db, user_id, Decimal("10.00"))
            return True, None
        except InsufficientFundsError:
            db.rollback()
            return False, "Insufficient balance"
        finally:
            db.close()

    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(debit_once) for _ in range(50)]
        for future in as_completed(futures):
            results.append(future.result())

    successful_debits = sum(1 for success, _ in results if success)
    failed_debits = sum(1 for success, _ in results if not success)
    assert successful_debits == 10
    assert failed_debits == 40

    balance_response = client.get(f"/wallets/{user_id}/balance")
    assert balance_response.status_code == 200
    assert Decimal(balance_response.json()["balance"]) == Decimal("0.00")

    ledger_response = client.get(f"/wallets/{user_id}/ledger?limit=200&offset=0")
    assert ledger_response.status_code == 200
    items = ledger_response.json()["items"]

    credit_entries = [entry for entry in items if entry["entry_type"] == "credit"]
    debit_entries = [entry for entry in items if entry["entry_type"] == "debit"]
    assert len(credit_entries) == 1
    assert len(debit_entries) == 10

    failure_reasons: dict[str, int] = {}
    for success, reason in results:
        if not success and reason:
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    final_balance = Decimal(balance_response.json()["balance"]).quantize(Decimal("0.00"))
    print("PHASE2_CONCURRENCY_CHECK: PASS")
    print(
        "successes="
        f"{successful_debits} failures={failed_debits} final_balance={final_balance} "
        f"debit_ledger_entries={len(debit_entries)} failure_reasons={failure_reasons}"
    )
