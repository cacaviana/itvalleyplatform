def test_user_with_permission_passes(client, make_token_fn):
    token = make_token_fn(
        tenant_id="clinica-abc",
        products=["genesis"],
        permissions={"genesis": ["leads"]},
    )
    r = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text


def test_user_without_permission_returns_403(client, make_token_fn):
    token = make_token_fn(
        tenant_id="clinica-abc",
        products=["genesis"],
        permissions={"genesis": ["deals"]},
    )
    r = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_user_without_permissions_dict_returns_403(client, make_token_fn):
    token = make_token_fn(tenant_id="clinica-abc")
    r = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
