from datetime import datetime


class HtmlReportBuilder:
    """Builds the enrollment run's HTML report.

    Reproduces the exact HTML string-building that previously lived
    inline in main.py (originally legacy_enrollment_processor.py:19-20,
    69-72, 78, 80-81): a header with a timestamp, one <tr> row per
    enrollment result (styled red on failure), and the closing markup.

    This class has no knowledge of SQLite, CSV parsing, enrollment
    status rules, or notification messages -- it only knows how to turn
    enrollment result values it's handed into HTML.
    """

    def __init__(self):
        self._html = ""

    def start(self):
        self._html = f"<html><body><h1>Enrollment Run: {datetime.now()}</h1><table border='1'>"
        self._html += "<tr><th>ID</th><th>Name</th><th>Course</th><th>Status</th></tr>"

    def add_result(self, student_id, student_name, course_code, status):
        if "FAILED" in status:
            self._html += f"<tr style='color:red;'><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"
        else:
            self._html += f"<tr><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"

    def render(self):
        return self._html + "</table></body></html>"

    def write(self, path):
        with open(path, "w") as report_file:
            report_file.write(self.render())
