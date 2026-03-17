from app.seed.master_prompts import seed_prompts

def test_list_prompts(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 48

def test_list_prompts_by_industry(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts?industry=healthcare")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    assert all(p["industry"] == "healthcare" for p in data)

def test_get_prompt(client, db):
    seed_prompts(db)
    resp = client.get("/api/v1/prompts/1")
    assert resp.status_code == 200
    assert "Modern Dental Clinic" in resp.json()["name"]

def test_update_prompt(client, db):
    seed_prompts(db)
    resp = client.patch("/api/v1/prompts/1", json={"prompt_text": "Updated prompt text"})
    assert resp.status_code == 200
    assert resp.json()["prompt_text"] == "Updated prompt text"
