def test_tenant_from_jwt_claims(client, make_token_fn):
    token = make_token_fn(tenant_id="clinica-abc", products=["genesis"])
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "clinica-abc"
    assert data["is_master"] is False
    assert data["products"] == ["genesis"]


def test_token_without_tenant_id_returns_404(client, make_token_fn):
    token = make_token_fn(tenant_id=None)
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_non_master_ignores_tenant_header(client, make_token_fn):
    token = make_token_fn(tenant_id="clinica-abc", products=["genesis"])
    r = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "outro-tenant",
        },
    )
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "clinica-abc"
