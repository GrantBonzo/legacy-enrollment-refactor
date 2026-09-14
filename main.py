from datetime import datetime

from infrastructure.sqlite_enrollment_repository import EnrollmentRepository
from infrastructure.csv_enrollment_reader import read_enrollment_rows
from infrastructure.console_email_notifier import send_notification
from domain.enrollment_rules import determine_status

# HARDCODED GLOBALS (unchanged from legacy_enrollment_processor.py)
DB_PATH = "university_enrollment.db"
CSV_PATH = "students.csv"


def run_legacy_enrollment():
    # 1. DATABASE SETUP -- now delegated to EnrollmentRepository.
    # Everything else below is intentionally left exactly as it was in
    # legacy_enrollment_processor.py; only the SQLite responsibility has
    # been extracted for this step.
    repository = EnrollmentRepository(DB_PATH)
    repository.create_schema()

    # 2. HTML REPORT SETUP (unchanged)
    html_report = f"<html><body><h1>Enrollment Run: {datetime.now()}</h1><table border='1'>"
    html_report += "<tr><th>ID</th><th>Name</th><th>Course</th><th>Status</th></tr>"

    # 3. FILE I/O -- now delegated to read_enrollment_rows().
    rows = read_enrollment_rows(CSV_PATH)
    if rows is None:
        print("ERROR: CSV file not found!")
        return

    # 4. THE GOD LOOP (unchanged, except CSV parsing and DB calls now go
    # through the extracted reader and repository)
    for student_id, student_name, course_code, credits, has_prereqs, override_code in rows:
        # 5. BUSINESS LOGIC -- status decision now delegated to determine_status().
        # Check if student already has too many credits
        current_credits = repository.get_current_enrolled_credits(student_id)

        status = determine_status(current_credits, credits, has_prereqs, override_code)

        # SIMULATED EMAIL (unchanged) -- message text is still built here,
        # keyed off the status returned by the domain rule.
        if status == "FAILED - CREDIT LIMIT EXCEEDED":
            send_notification(f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Credit limit).")
        elif status == "ENROLLED":
            send_notification(f"SENDING EMAIL TO: {student_name} -> Successfully enrolled in {course_code}.")
        elif status == "ENROLLED (OVERRIDE)":
            send_notification(f"SENDING EMAIL TO: {student_name} -> Enrolled in {course_code} with Dean override.")
        else:
            send_notification(f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Missing Prereqs).")

        # 6. DATABASE EXECUTION -- now delegated to EnrollmentRepository.
        repository.save_result(student_id, student_name, course_code, credits, status)

        # 7. HTML GENERATION (unchanged)
        if "FAILED" in status:
            html_report += f"<tr style='color:red;'><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"
        else:
            html_report += f"<tr><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"

    # 8. TEARDOWN AND SAVING -- now delegated to EnrollmentRepository.
    repository.commit()
    repository.close()

    html_report += "</table></body></html>"

    with open("enrollment_report.html", "w") as report_file:
        report_file.write(html_report)

    print("Enrollment processing complete. Report generated.")


if __name__ == "__main__":
    run_legacy_enrollment()
