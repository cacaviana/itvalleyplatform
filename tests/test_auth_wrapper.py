"""
Garante que o wrapper consertou o bug do itvalleysecurity 0.1.0 onde
token inválido vazava como 500.
"""


def test_no_token_returns_401(client):
    r = client.get("/me")
    assert r.status_code == 401


def test_garbage_token_returns_401_not_500(client):
    r = client.get("/me", headers={"Authorization": "Bearer xxx.yyy.zzz"})
    assert r.status_code == 401, r.text


def test_signature_mismatch_returns_401(client, make_token_fn):
    token = make_token_fn()
    bad = token[:-4] + "AAAA"
    r = client.get("/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401, r.text
