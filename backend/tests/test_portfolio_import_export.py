"""Endpoint tests for Phase C portfolio import / export / tax-report.

These exercise the full HTTP + DB path (auth, CSRF, ownership). They are offline-
safe: live quote lookups fail gracefully and fall back to avg_cost, so no network
is required for deterministic assertions.
"""

PW = "securepass123"


async def _login(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": PW})
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": PW})
    return r.json()["csrf_token"]


async def _make_portfolio(client, csrf, name="Test"):
    r = await client.post(
        "/api/v1/portfolio", json={"name": name},
        headers={"X-CSRF-Token": csrf},
    )
    return r.json()["id"]


async def test_import_creates_and_merges_positions(client):
    csrf = await _login(client, "imp1@example.com")
    pid = await _make_portfolio(client, csrf)

    csv = b"ticker,quantity,avg_cost\nTCS,10,3500\nTCS,10,3700\nINFY,5,1500\n"
    r = await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("holdings.csv", csv, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # TCS rows merged within the file → 2 unique tickers imported
    assert body["imported"] == 2
    assert body["added"] == 2

    # The portfolio now has 2 positions; TCS averaged to 3600
    detail = (await client.get(f"/api/v1/portfolio/{pid}")).json()
    tcs = next(p for p in detail["positions"] if p["ticker"] == "TCS")
    assert tcs["quantity"] == 20
    assert tcs["avg_cost"] == 3600


async def test_import_merges_with_existing_position(client):
    csrf = await _login(client, "imp2@example.com")
    pid = await _make_portfolio(client, csrf)
    await client.post(
        f"/api/v1/portfolio/{pid}/positions",
        json={"ticker": "TCS", "quantity": 10, "avg_cost": 3000},
        headers={"X-CSRF-Token": csrf},
    )
    csv = b"ticker,quantity,avg_cost\nTCS,10,4000\n"
    r = await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("h.csv", csv, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.json()["merged"] == 1
    detail = (await client.get(f"/api/v1/portfolio/{pid}")).json()
    tcs = next(p for p in detail["positions"] if p["ticker"] == "TCS")
    assert tcs["quantity"] == 20
    assert tcs["avg_cost"] == 3500


async def test_import_rejects_bad_file(client):
    csrf = await _login(client, "imp3@example.com")
    pid = await _make_portfolio(client, csrf)
    r = await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 422


async def test_export_formats(client):
    csrf = await _login(client, "exp1@example.com")
    pid = await _make_portfolio(client, csrf, name="Growth")
    csv = b"ticker,quantity,avg_cost\nTCS,10,3500\n"
    await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("h.csv", csv, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )

    rc = await client.get(f"/api/v1/portfolio/{pid}/export?format=csv")
    assert rc.status_code == 200
    assert rc.headers["content-type"].startswith("text/csv")
    assert b"TCS" in rc.content

    rx = await client.get(f"/api/v1/portfolio/{pid}/export?format=xlsx")
    assert rx.status_code == 200
    assert rx.content[:2] == b"PK"

    rp = await client.get(f"/api/v1/portfolio/{pid}/export?format=pdf")
    assert rp.status_code == 200
    assert rp.content[:5] == b"%PDF-"


async def test_export_bad_format(client):
    csrf = await _login(client, "exp2@example.com")
    pid = await _make_portfolio(client, csrf)
    r = await client.get(f"/api/v1/portfolio/{pid}/export?format=json")
    assert r.status_code == 400


async def test_tax_report(client):
    csrf = await _login(client, "tax1@example.com")
    pid = await _make_portfolio(client, csrf)
    csv = b"ticker,quantity,avg_cost\nTCS,10,3500\n"
    await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("h.csv", csv, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    r = await client.get(f"/api/v1/portfolio/{pid}/tax-report")
    assert r.status_code == 200
    body = r.json()
    assert "long_term" in body and "short_term" in body
    # Freshly added → short term
    assert body["short_term"]["positions"] == 1


async def test_import_requires_ownership(client):
    csrf_a = await _login(client, "owner@example.com")
    pid = await _make_portfolio(client, csrf_a)
    # Second user cannot import into the first user's portfolio
    csrf_b = await _login(client, "intruder@example.com")
    r = await client.post(
        f"/api/v1/portfolio/{pid}/import",
        files={"file": ("h.csv", b"ticker,quantity,avg_cost\nTCS,1,100\n", "text/csv")},
        headers={"X-CSRF-Token": csrf_b},
    )
    assert r.status_code == 404
