def test_master_without_header_uses_jwt_tenant(client, make_token_fn):
    token = make_token_fn(tenant_id="it-valley", is_master=True)
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_master"] is True
    assert body["tenant_id"] == "it-valley"


def test_master_with_header_picks_target_tenant(client, make_token_fn):
    token = make_token_fn(tenant_id="it-valley", is_master=True)
    r = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "clinica-abc",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_master"] is True
    assert body["tenant_id"] == "clinica-abc"


def test_master_bypasses_permission_check(client, make_token_fn):
    # master sem 'leads' nas permissions ainda passa
    token = make_token_fn(
        tenant_id="it-valley",
        is_master=True,
        permissions={"genesis": []},
    )
    r = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
