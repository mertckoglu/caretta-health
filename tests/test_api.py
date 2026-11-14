import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path / "test.db"))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_reference_endpoints(client):
    inds = client.get("/indicators").json()
    assert {i["key"] for i in inds} >= {"heart_rate", "blood_glucose", "mood"}
    spo2 = next(i for i in inds if i["key"] == "spo2")
    assert spo2["thresholds"]["green"] == [[95, None]]
    assert "radiation" in client.get("/hazards").json()
    assert "heart" in client.get("/regions").json()
    assert client.get("/indicators", params={"environment": "nowhere"}).status_code == 422


def test_post_and_list_reading(client):
    r = client.post("/readings", json={"astronaut_id": "CDR", "indicator": "heart_rate", "value": 128})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "red" and body["id"] == 1
    lst = client.get("/readings", params={"astronaut_id": "CDR"}).json()
    assert len(lst) == 1 and lst[0]["value"] == 128
    assert client.get("/astronauts").json() == ["CDR"]


def test_validation_errors(client):
    bad_ind = client.post("/readings", json={"astronaut_id": "CDR", "indicator": "x", "value": 1})
    assert bad_ind.status_code == 422
    implausible = client.post("/readings", json={"astronaut_id": "CDR", "indicator": "spo2", "value": 140})
    assert implausible.status_code == 422
    bad_env = client.post(
        "/readings", json={"astronaut_id": "CDR", "indicator": "spo2", "value": 97, "environment": "venus"}
    )
    assert bad_env.status_code == 422


def test_delete_reading(client):
    rid = client.post("/readings", json={"astronaut_id": "PLT", "indicator": "mood", "value": 4}).json()["id"]
    assert client.delete(f"/readings/{rid}").status_code == 204
    assert client.delete(f"/readings/{rid}").status_code == 404


def test_status_404_without_data(client):
    assert client.get("/status/NOBODY").status_code == 404


def test_simulate_then_status_and_report(client):
    r = client.post("/simulate", json={"astronaut_id": "CDR", "days": 30})
    assert r.status_code == 201 and r.json()["inserted"] == 300
    # replace=True must not duplicate
    client.post("/simulate", json={"astronaut_id": "CDR", "days": 30})
    assert len(client.get("/readings", params={"astronaut_id": "CDR", "indicator": "mood"}).json()) == 30

    s = client.get("/status/CDR").json()
    assert s["overall"] in {"green", "yellow", "red"}
    assert set(s["regions"]) >= {"heart", "brain", "lungs"}
    assert len(s["indicators"]) == 10
    assert s["cumulative_dose_msv"] > 0

    recs = client.get("/recommendations/CDR").json()
    assert isinstance(recs, list)
    report = client.get("/report/CDR")
    assert report.status_code == 200 and "Caretta health downlink" in report.text


def test_environments_are_separate_datasets(client):
    client.post("/simulate", json={"astronaut_id": "CDR", "days": 10, "environment": "iss"})
    client.post("/simulate", json={"astronaut_id": "CDR", "days": 10, "environment": "mars_base"})
    # replacing the Mars mission must not touch the ISS one
    client.post("/simulate", json={"astronaut_id": "CDR", "days": 10, "environment": "mars_base"})
    iss = client.get("/readings", params={"astronaut_id": "CDR", "environment": "iss"}).json()
    mars = client.get("/readings", params={"astronaut_id": "CDR", "environment": "mars_base"}).json()
    assert len(iss) == 100 and len(mars) == 100
    assert {r["environment"] for r in mars} == {"mars_base"}
    assert client.get("/status/CDR", params={"environment": "mars_base"}).json()["environment"] == "mars_base"
    assert client.get("/status/CDR", params={"environment": "rover"}).status_code == 404
    assert client.get("/astronauts", params={"environment": "rover"}).json() == []


def test_db_environment_helpers(tmp_path):
    from app.api import db
    from app.core.simulate import simulate_crew

    conn = db.connect(tmp_path / "x.db")
    db.insert_dataframe(conn, simulate_crew(days=3, environment="iss"))
    db.insert_dataframe(conn, simulate_crew(days=3, environment="rover"))
    assert db.count_readings(conn, "iss") == db.count_readings(conn, "rover") == 120
    assert db.delete_environment(conn, "rover") == 120
    assert db.count_readings(conn, "rover") == 0 and db.count_readings(conn) == 120
    assert db.list_astronauts(conn, "iss") == ["CDR", "MS1", "MS2", "PLT"]


def _png_bytes(size=(800, 600), color=(200, 40, 50)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def test_photos_roundtrip(tmp_path):
    from app.api import db

    conn = db.connect(tmp_path / "p.db")
    pid = db.insert_photo(conn, "CDR", _png_bytes(), "image/png", environment="mars_base", category="skin",
                          caption=" rash ")
    df = db.fetch_photos(conn, "CDR")
    assert len(df) == 1 and df.iloc[0]["caption"] == "rash" and df.iloc[0]["category"] == "skin"
    full = db.photo_path(conn, df.iloc[0]["filename"])
    thumb = db.thumb_path(conn, df.iloc[0]["filename"])
    assert full.exists() and thumb.exists() and thumb != full
    assert full.parent == tmp_path / "photos"
    from PIL import Image

    with Image.open(thumb) as im:
        assert max(im.size) <= db.THUMB_PX
    assert db.fetch_photos(conn, environment="iss").empty
    assert db.update_photo(conn, pid, caption="healing", category="wound")
    assert db.fetch_photos(conn).iloc[0]["category"] == "wound"
    assert db.delete_photo(conn, pid) and not full.exists() and not thumb.exists()
    assert not db.delete_photo(conn, pid)


def test_photo_validation(tmp_path):
    from app.api import db

    conn = db.connect(tmp_path / "p.db")
    for bad in [dict(data=b""), dict(data=b"not an image"), dict(data=_png_bytes(), mime="application/pdf"),
                dict(data=_png_bytes(), category="selfie")]:
        args = {"mime": "image/png", "category": "other", **bad}
        with pytest.raises(ValueError):
            db.insert_photo(conn, "CDR", args["data"], args["mime"], category=args["category"])
    assert db.fetch_photos(conn).empty
    assert list((tmp_path / "photos").glob("*")) == [] if (tmp_path / "photos").exists() else True
