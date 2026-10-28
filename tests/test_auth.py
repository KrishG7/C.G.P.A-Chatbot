"""Tests for signup, login, teacher approval and role checks. No network: Supabase is replaced by
small in-memory fakes (a table store and an Auth service)."""
import io
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import app as backend  # noqa: E402


class Table:
    def __init__(self, rows):
        self.rows, self.filters, self.op, self.payload = rows, [], "select", None

    def select(self, *_a, **_k):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        def hit(r):
            return all(str(r.get(c)) == str(v) for c, v in self.filters)

        if self.op == "insert":
            self.rows.append(dict(self.payload))
            return types.SimpleNamespace(data=[self.payload])
        if self.op == "update":
            for r in self.rows:
                if hit(r):
                    r.update(self.payload)
            return types.SimpleNamespace(data=[])
        if self.op == "delete":
            self.rows[:] = [r for r in self.rows if not hit(r)]
            return types.SimpleNamespace(data=[])
        return types.SimpleNamespace(data=[dict(r) for r in self.rows if hit(r)])


class DB:
    def __init__(self):
        self.tables = {"profiles": [], "classes": [], "students": [], "attendance_records": [], "conversations": []}

    def table(self, name):
        return Table(self.tables[name])


class Auth:
    def __init__(self):
        self.users = {}

    def sign_up(self, creds):
        self.users[creds["email"]] = creds["password"]

    def sign_in_with_password(self, creds):
        if self.users.get(creds["email"]) != creds["password"]:
            raise ValueError("bad credentials")
        return types.SimpleNamespace(session=types.SimpleNamespace(access_token="tok:" + creds["email"]))

    def get_user(self, token):
        if not token.startswith("tok:"):
            raise ValueError("bad token")
        return types.SimpleNamespace(user=types.SimpleNamespace(email=token[4:]))


@pytest.fixture()
def env(monkeypatch):
    db, auth = DB(), Auth()
    monkeypatch.setattr(backend, "supabase", db)
    monkeypatch.setattr(backend, "new_client", lambda: types.SimpleNamespace(auth=auth))
    backend.app.config["TESTING"] = True
    return backend.app.test_client(), db, auth


def post(c, path, token=None, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return c.post(path, headers=headers, **kw)


def signup(c, email, role, password="longenough1"):
    return c.post("/signup", json={"email": email, "password": password, "role": role})


def test_student_is_approved_teacher_is_not(env):
    c, db, _ = env
    assert signup(c, "S@x.com", "student").status_code == 200
    assert signup(c, "t@x.com", "teacher").status_code == 200
    profiles = {p["email"]: p for p in db.tables["profiles"]}
    assert profiles["s@x.com"]["approved"] is True            # emails are lower-cased
    assert profiles["t@x.com"]["approved"] is False


def test_signup_cannot_create_an_admin_or_use_a_short_password(env):
    c, db, _ = env
    assert signup(c, "a@x.com", "admin").status_code == 400
    assert signup(c, "a@x.com", "student", password="short").status_code == 400
    assert db.tables["profiles"] == []


def test_signup_does_not_overwrite_a_pre_created_admin(env):
    c, db, _ = env
    db.tables["profiles"].append({"email": "boss@x.com", "role": "admin", "approved": True})
    signup(c, "boss@x.com", "student")
    assert db.tables["profiles"] == [{"email": "boss@x.com", "role": "admin", "approved": True}]


def test_login_rules(env):
    c, _, _ = env
    signup(c, "t@x.com", "teacher")
    assert c.post("/login", json={"email": "t@x.com", "password": "wrong-pass"}).status_code == 401
    assert c.post("/login", json={"email": "t@x.com", "password": "longenough1"}).status_code == 403  # unapproved
    signup(c, "s@x.com", "student")
    r = c.post("/login", json={"email": "s@x.com", "password": "longenough1"})
    assert r.status_code == 200 and r.json["role"] == "student" and r.json["token"] == "tok:s@x.com"


def test_protected_routes_need_a_valid_role(env):
    c, _, _ = env
    signup(c, "s@x.com", "student")
    assert post(c, "/get_classes", json={}).status_code == 401
    assert post(c, "/get_classes", token="garbage", json={}).status_code == 401
    assert post(c, "/get_classes", token="tok:s@x.com", json={}).status_code == 403   # a student is not a teacher
    assert post(c, "/admin/pending", token="tok:s@x.com", json={}).status_code == 403


def test_admin_approves_a_teacher(env):
    c, db, _ = env
    db.tables["profiles"].append({"email": "boss@x.com", "role": "admin", "approved": True})
    signup(c, "boss@x.com", "student")                       # creates the Auth user for the admin row
    signup(c, "t@x.com", "teacher")
    assert post(c, "/admin/approve", token="tok:t@x.com", json={"email": "t@x.com"}).status_code == 403   # a teacher cannot approve themselves
    pending = post(c, "/admin/pending", token="tok:boss@x.com", json={}).json["pending"]
    assert [p["email"] for p in pending] == ["t@x.com"]
    assert post(c, "/admin/approve", token="tok:boss@x.com", json={"email": "t@x.com"}).status_code == 200
    assert c.post("/login", json={"email": "t@x.com", "password": "longenough1"}).status_code == 200


def approved_teacher(c, db, email):
    signup(c, email, "teacher")
    next(p for p in db.tables["profiles"] if p["email"] == email)["approved"] = True
    return "tok:" + email


def test_teacher_identity_comes_from_the_token_not_the_body(env):
    c, db, _ = env
    tok = approved_teacher(c, db, "a@x.com")
    post(c, "/create_class", token=tok, json={"email": "victim@x.com", "name": "CSE-A"})
    assert db.tables["classes"] == [{"teacher_email": "a@x.com", "class_name": "CSE-A"}]


def test_teacher_cannot_upload_to_another_teachers_class(env):
    c, db, _ = env
    tok = approved_teacher(c, db, "a@x.com")
    db.tables["classes"].append({"id": 7, "teacher_email": "b@x.com", "class_name": "ECE-B"})
    csv = (io.BytesIO(b"Roll Number,Name\n1,Ann\n"), "r.csv")
    r = c.post("/upload_smart_roster", headers={"Authorization": f"Bearer {tok}"},
               data={"file": csv, "class_id": "7"}, content_type="multipart/form-data")
    assert r.status_code == 403
    assert db.tables["students"] == []


def test_guest_has_no_identity(env):
    c, _, _ = env
    with backend.app.test_request_context("/chat", headers={"Authorization": "Bearer tok:nobody@x.com"}):
        assert backend.current_user() is None                 # a valid token but no profile row
    with backend.app.test_request_context("/chat"):
        assert backend.current_user() is None
