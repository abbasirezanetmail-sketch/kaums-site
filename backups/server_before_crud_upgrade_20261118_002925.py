
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import threading

PROJECT = Path(__file__).resolve().parent
DB = PROJECT / "database"
LOCK = threading.Lock()

COLLECTIONS = {
    "universities": {
        "file": "universities.json",
        "id": "university_id",
        "prefix": "UNI",
        "name": "university_name",
        "required": ["university_name"]
    },
    "fields": {
        "file": "fields.json",
        "id": "field_id",
        "prefix": "FLD",
        "name": "field_name",
        "required": ["field_name", "university_id"]
    },
    "categories": {
        "file": "categories.json",
        "id": "category_id",
        "prefix": "CAT",
        "name": "category_name",
        "required": ["category_name"]
    },
    "terms": {
        "file": "terms.json",
        "id": "term_id",
        "prefix": "TERM",
        "name": "term_name",
        "required": ["term_name", "university_id", "field_id"]
    },
    "courses": {
        "file": "courses.json",
        "id": "course_id",
        "prefix": "CRS",
        "name": "course_name",
        "required": ["course_name", "term_id", "university_id", "field_id"]
    },
    "resources": {
        "file": "resources.json",
        "id": "resource_id",
        "prefix": "MED",
        "name": "title",
        "required": ["term_id", "course_id", "title", "resource_type", "download_url"]
    }
}

def read_json(filename):
    with open(DB / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(filename, data):
    path = DB / filename
    temp = path.with_suffix(".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
    temp.replace(path)

def next_id(prefix, records, id_key):
    numbers = []
    for item in records:
        value = str(item.get(id_key, ""))
        if value.startswith(prefix + "-"):
            suffix = value.split("-")[-1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    return f"{prefix}-{max(numbers, default=0) + 1:06d}"

def active_record(records, id_key, value):
    return next(
        (x for x in records
         if x.get(id_key) == value
         and str(x.get("status", "Active")).lower() == "active"),
        None
    )

def validate_references(collection, data):
    if collection == "fields":
        return active_record(read_json("universities.json"), "university_id",
                             data.get("university_id")) is not None

    if collection == "terms":
        universities = read_json("universities.json")
        fields = read_json("fields.json")
        field = active_record(fields, "field_id", data.get("field_id"))
        university = active_record(universities, "university_id",
                                   data.get("university_id"))
        return bool(field and university and
                    field.get("university_id") == data.get("university_id"))

    if collection == "courses":
        terms = read_json("terms.json")
        term = active_record(terms, "term_id", data.get("term_id"))
        return bool(term and
                    term.get("university_id") == data.get("university_id") and
                    term.get("field_id") == data.get("field_id"))

    if collection == "resources":
        terms = read_json("terms.json")
        courses = read_json("courses.json")
        term = active_record(terms, "term_id", data.get("term_id"))
        course = active_record(courses, "course_id", data.get("course_id"))
        if not term or not course:
            return False
        if course.get("term_id") != data.get("term_id"):
            return False
        if data.get("university_id") != term.get("university_id"):
            return False
        if data.get("field_id") != term.get("field_id"):
            return False
        if data.get("category_id"):
            categories = read_json("categories.json")
            if not active_record(categories, "category_id",
                                 data.get("category_id")):
                return False
        return True

    return True

def has_dependencies(collection, record_id):
    dependencies = {
        "universities": [
            ("fields.json", "university_id"),
            ("terms.json", "university_id"),
            ("courses.json", "university_id"),
            ("resources.json", "university_id")
        ],
        "fields": [
            ("terms.json", "field_id"),
            ("courses.json", "field_id"),
            ("resources.json", "field_id")
        ],
        "categories": [
            ("resources.json", "category_id")
        ],
        "terms": [
            ("courses.json", "term_id"),
            ("resources.json", "term_id")
        ],
        "courses": [
            ("resources.json", "course_id")
        ]
    }
    for filename, key in dependencies.get(collection, []):
        if any(x.get(key) == record_id for x in read_json(filename)):
            return True
    return False

class MedLibraryHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT), **kwargs)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > 1_000_000:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.path = "/admin.html"
            return super().do_GET()

        if path == "/api/dashboard":
            with LOCK:
                self.send_json({
                    "resources": len(read_json("resources.json")),
                    "courses": len(read_json("courses.json")),
                    "terms": len(read_json("terms.json")),
                    "universities": len(read_json("universities.json")),
                    "fields": len(read_json("fields.json")),
                    "categories": len(read_json("categories.json"))
                })
            return

        if path.startswith("/api/"):
            collection = path.split("/")[2]
            if collection in COLLECTIONS:
                with LOCK:
                    self.send_json(read_json(COLLECTIONS[collection]["file"]))
                return

            self.send_json({"error": "Route not found"}, 404)
            return

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) != 2 or parts[0] != "api" or parts[1] not in COLLECTIONS:
            self.send_json({"error": "Route not found"}, 404)
            return

        collection = parts[1]
        config = COLLECTIONS[collection]

        try:
            data = self.read_body()

            missing = [
                key for key in config["required"]
                if not str(data.get(key) or "").strip()
            ]
            if missing:
                self.send_json({"error": "Missing fields: " + ", ".join(missing)}, 400)
                return

            with LOCK:
                records = read_json(config["file"])

                if collection == "resources":
                    courses = read_json("courses.json")
                    course = active_record(courses, "course_id", data.get("course_id"))
                    if not course:
                        self.send_json({"error": "Invalid course"}, 400)
                        return

                    term = active_record(read_json("terms.json"), "term_id",
                                         data.get("term_id"))
                    if not term:
                        self.send_json({"error": "Invalid term"}, 400)
                        return

                    data.setdefault("university_id", term.get("university_id"))
                    data.setdefault("field_id", term.get("field_id"))
                    data.setdefault("category_id", None)

                if not validate_references(collection, data):
                    self.send_json({"error": "Invalid or inconsistent references"}, 400)
                    return

                record_id = next_id(config["prefix"], records, config["id"])
                new_record = {
                    config["id"]: record_id,
                    **data,
                    "status": "Active"
                }

                if collection == "resources":
                    new_record.update({
                        "course": course["course_name"],
                        "file_name": data.get("file_name"),
                        "file_path": data.get("file_path"),
                        "is_duplicate": False,
                        "access_type": data.get("access_type", "Direct")
                    })
                    for key in ["professor", "academic_year", "description",
                                "tags", "download_url", "source_url", "file_format"]:
                        new_record.setdefault(key, None)

                records.append(new_record)
                write_json(config["file"], records)

            self.send_json({
                "success": True,
                "id": record_id,
                "message": "Record created successfully"
            }, 201)

        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:
            self.send_json({"error": str(error)}, 500)

    def do_PUT(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) != 3 or parts[0] != "api" or parts[1] not in COLLECTIONS:
            self.send_json({"error": "Route not found"}, 404)
            return

        collection, record_id = parts[1], parts[2]
        config = COLLECTIONS[collection]

        try:
            data = self.read_body()
            with LOCK:
                records = read_json(config["file"])
                record = next((x for x in records
                               if x.get(config["id"]) == record_id), None)

                if not record:
                    self.send_json({"error": "Record not found"}, 404)
                    return

                updated = {**record, **data}
                updated[config["id"]] = record_id

                if not validate_references(collection, updated):
                    self.send_json({"error": "Invalid or inconsistent references"}, 400)
                    return

                records[records.index(record)] = updated
                write_json(config["file"], records)

            self.send_json({"success": True, "message": "Record updated"})

        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:
            self.send_json({"error": str(error)}, 500)

    def do_DELETE(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) != 3 or parts[0] != "api" or parts[1] not in COLLECTIONS:
            self.send_json({"error": "Route not found"}, 404)
            return

        collection, record_id = parts[1], parts[2]
        config = COLLECTIONS[collection]

        with LOCK:
            records = read_json(config["file"])
            record = next((x for x in records
                           if x.get(config["id"]) == record_id), None)

            if not record:
                self.send_json({"error": "Record not found"}, 404)
                return

            if collection == "resources" or has_dependencies(collection, record_id):
                record["status"] = "Inactive"
                message = "Record deactivated because it is in use"
            else:
                records.remove(record)
                message = "Record deleted"

            write_json(config["file"], records)

        self.send_json({"success": True, "message": message})

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), MedLibraryHandler)
    print("MedLibrary server running at http://127.0.0.1:8000")
    server.serve_forever()
