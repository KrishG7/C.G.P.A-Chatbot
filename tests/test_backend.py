"""Regression tests for the C.G.P.A. backend. No network or API key needed.

Run from the project root:  pip install pytest && pytest tests/
"""
import os
import sys
import types

import pytest

os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import app as backend  # noqa: E402


class FakeTable:
    """The slice of the Supabase query builder the endpoints use, over a list of dict rows."""

    def __init__(self, rows):
        self.rows, self.filters, self.op, self.payload = rows, [], "select", None

    def select(self, *_args, **_kwargs):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
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
        def match(r):
            return all(str(r.get(c)) == str(v) for c, v in self.filters)

        if self.op == "insert":
            unknown = set(self.payload) - {"id", "class_name", "teacher_email", "student_id", "class_id"}
            if unknown:  # what PostgREST does for a column the table does not have
                raise RuntimeError(f"Could not find the {sorted(unknown)[0]!r} column")
            self.rows.append(dict(self.payload))
            return types.SimpleNamespace(data=[self.payload])
        if self.op == "delete":
            self.rows[:] = [r for r in self.rows if not match(r)]
            return types.SimpleNamespace(data=[])
        return types.SimpleNamespace(data=[r for r in self.rows if match(r)])


class FakeSupabase:
    def __init__(self):
        self.tables = {"classes": [], "students": []}

    def table(self, name):
        return FakeTable(self.tables[name])


@pytest.fixture()
def client(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(backend, "supabase", fake)
    monkeypatch.setattr(backend, "current_user", lambda: {"email": "t@x.com", "role": "teacher", "approved": True})
    backend.app.config["TESTING"] = True
    return backend.app.test_client(), fake


def test_create_class_maps_email_to_teacher_email(client):
    c, fake = client
    r = c.post("/create_class", json={"email": "t@x.com", "name": "CSE-A"})
    assert r.status_code == 200
    assert fake.tables["classes"] == [{"teacher_email": "t@x.com", "class_name": "CSE-A"}]


def test_create_class_rejects_missing_fields(client):
    c, _ = client
    assert c.post("/create_class", json={"email": "t@x.com"}).status_code == 400


def test_delete_student_is_scoped_to_one_class(client):
    c, fake = client
    fake.tables["students"] += [
        {"student_id": "101", "class_id": 1, "teacher_email": "t@x.com"},
        {"student_id": "101", "class_id": 2, "teacher_email": "b@x.com"},
    ]
    r = c.post("/delete_student", json={"id": "101", "class_id": 1})
    assert r.status_code == 200
    assert fake.tables["students"] == [{"student_id": "101", "class_id": 2, "teacher_email": "b@x.com"}]


def test_delete_student_without_class_is_refused(client):
    c, fake = client
    fake.tables["students"].append({"student_id": "101", "class_id": 1})
    assert c.post("/delete_student", json={"id": "101"}).status_code == 400
    assert len(fake.tables["students"]) == 1


# Retrieval: (question, fact that must appear in the retrieved context). Taken from data/knowledge_source.
RETRIEVAL_CASES = [
    ("Who is the chairperson of the Anti-Ragging Committee?", "Vanita Jain"),
    ("What is the email of the anti ragging committee?", "arc@fot.du.ac.in"),
    ("What is the landline number of the faculty office?", "011-27662880"),
    ("What are the credits and L-T-P of Data Structures in first year?", "Data Structures"),
    ("Syllabus of Digital Electronics I", "Digital Electronics"),
    ("Which library can FOT students access?", "Central Science Library"),
    ("Tell me about Mathematics-II course", "Mathematics-II"),
    ("What is the email of the committee for differently abled?", "cda@fot.du.ac.in"),
]


@pytest.mark.parametrize("question,fact", RETRIEVAL_CASES)
def test_retrieval_finds_fact(question, fact):
    backend.load_brain()
    assert fact.lower() in backend.get_context(question).lower()


def test_knowledge_base_includes_every_source_file():
    """The index must be rebuilt (python backend/process_data.py) when data files change."""
    import json
    kb = json.load(open(os.path.join(os.path.dirname(backend.__file__), "knowledge_base.json")))
    tags = {c.split("]")[0].lstrip("[") for c in kb}
    data_dir = os.path.join(os.path.dirname(backend.__file__), "..", "data", "knowledge_source")
    for f in os.listdir(data_dir):
        if f.endswith(".txt") and not f.startswith("."):
            assert f.replace(".txt", "").replace("_", " ").title() in tags, f"{f} is missing from the index"


def test_extract_action_handles_fence_and_trailing_prose():
    reply = '```json\n{"action": "analyze_data", "operator": "<", "value": 75}\n```\nStudents below 75%: none.'
    assert backend.extract_action(reply) == {"action": "analyze_data", "operator": "<", "value": 75}


def test_extract_action_handles_leading_prose_and_plain_json():
    assert backend.extract_action('Sure. {"action": "update_attendance", "ids": ["1"]}')["ids"] == ["1"]
    assert backend.extract_action('{"action": "x"}') == {"action": "x"}


def test_extract_action_rejects_text_without_json():
    with pytest.raises(ValueError):
        backend.extract_action("I don't have that information.")


def test_attach_attendance_uses_live_records():
    students = [
        {"student_id": "1", "class_id": 1, "details": {"Attendance": "0%"}},
        {"student_id": "2", "class_id": 1, "details": {"Attendance": "0%"}},
        {"student_id": "9", "class_id": 2, "details": {"Attendance": "0%"}},
    ]
    records = [
        {"student_id": "1", "class_id": 1, "date": "2026-10-27", "status": "Present"},
        {"student_id": "2", "class_id": 1, "date": "2026-10-27", "status": "Absent"},
        {"student_id": "1", "class_id": 1, "date": "2026-10-28", "status": "Absent"},
        {"student_id": "2", "class_id": 1, "date": "2026-10-28", "status": "Present"},
    ]
    out = backend.attach_attendance(students, records)
    assert out[0]["details"]["Attendance"] == "50%"
    assert out[1]["details"]["Attendance"] == "50%"
    assert out[2]["details"]["Attendance"] == "0%"   # class 2 has no records: keep the stored value
