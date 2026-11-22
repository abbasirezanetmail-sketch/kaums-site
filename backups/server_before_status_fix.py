from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading

PROJECT = Path(__file__).resolve().parent
DB = PROJECT / "database"

LOCK = threading.Lock()

def read_json(filename):
    path = DB / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(filename, data):
    path = DB / filename
    temp = path.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)

    temp.replace(path)

class MedLibraryHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT), **kwargs)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        routes = {
            "/api/resources": "resources.json",
            "/api/courses": "courses.json",
            "/api/terms": "terms.json"
        }

        if self.path == "/api/dashboard":
            with LOCK:
                self.send_json({
                    "resources": len(read_json("resources.json")),
                    "courses": len(read_json("courses.json")),
                    "terms": len(read_json("terms.json"))
                })
            return

        if self.path in routes:
            with LOCK:
                self.send_json(read_json(routes[self.path]))
            return

        if self.path == "/":
            self.path = "/admin.html"

        super().do_GET()

    def do_POST(self):
        if self.path != "/api/resources":
            self.send_json({"error": "Route not found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 1_000_000:
                self.send_json({"error": "Invalid request size"}, 400)
                return

            data = json.loads(self.rfile.read(length).decode("utf-8"))

            required = ["term_id", "course_id", "title", "resource_type", "download_url"]
            missing = [key for key in required if not str(data.get(key) or "").strip()]

            if missing:
                self.send_json({"error": "Missing fields: " + ", ".join(missing)}, 400)
                return

            with LOCK:
                terms = read_json("terms.json")
                courses = read_json("courses.json")
                resources = read_json("resources.json")

                term = next((x for x in terms if x["term_id"] == data["term_id"]), None)
                course = next((x for x in courses if x["course_id"] == data["course_id"]), None)

                if not term or not course:
                    self.send_json({"error": "Invalid term or course"}, 400)
                    return

                if course["term_id"] != data["term_id"]:
                    self.send_json({"error": "Course does not belong to selected term"}, 400)
                    return

                existing_ids = [
                    int(x["resource_id"].split("-")[-1])
                    for x in resources
                    if str(x.get("resource_id", "")).startswith("MED-")
                    and x["resource_id"].split("-")[-1].isdigit()
                ]

                next_id = max(existing_ids, default=0) + 1
                resource_id = f"MED-{next_id:06d}"

                new_resource = {
                    "resource_id": resource_id,
                    "term_id": data["term_id"],
                    "course_id": data["course_id"],
                    "course": course["course_name"],
                    "title": data["title"].strip(),
                    "resource_type": data["resource_type"],
                    "professor": data.get("professor") or None,
                    "academic_year": data.get("academic_year") or None,
                    "file_name": None,
                    "file_path": None,
                    "description": data.get("description") or None,
                    "tags": data.get("tags") or [],
                    "is_duplicate": False,
                    "status": data.get("status", "Active"),
                    "download_url": data["download_url"].strip(),
                    "source_url": data.get("source_url") or None,
                    "file_format": data.get("file_format") or None,
                    "access_type": "Direct"
                }

                resources.append(new_resource)
                write_json("resources.json", resources)

            self.send_json({
                "success": True,
                "resource_id": resource_id,
                "message": "Resource saved successfully"
            }, 201)

        except Exception as error:
            self.send_json({"error": str(error)}, 500)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), MedLibraryHandler)
    print("MedLibrary server running at http://127.0.0.1:8000")
    server.serve_forever()
