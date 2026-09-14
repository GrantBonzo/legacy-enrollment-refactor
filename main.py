from infrastructure.sqlite_enrollment_repository import EnrollmentRepository
from infrastructure.csv_enrollment_reader import read_enrollment_rows
from infrastructure.console_email_notifier import send_notification
from domain.enrollment_rules import determine_status
from domain.notifications import build_notification_message
from presentation.html_report_builder import HtmlReportBuilder

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

    # 2. HTML REPORT SETUP -- now delegated to HtmlReportBuilder.
    report_builder = HtmlReportBuilder()
    report_builder.start()

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

        # SIMULATED EMAIL -- message text now delegated to
        # build_notification_message(); only the "sending" side effect
        # goes through send_notification().
        message = build_notification_message(student_name, course_code, status)
        send_notification(message)

        # 6. DATABASE EXECUTION -- now delegated to EnrollmentRepository.
        repository.save_result(student_id, student_name, course_code, credits, status)

        # 7. HTML GENERATION -- now delegated to HtmlReportBuilder.
        report_builder.add_result(student_id, student_name, course_code, status)

    # 8. TEARDOWN AND SAVING -- now delegated to EnrollmentRepository.
    repository.commit()
    repository.close()

    report_builder.write("enrollment_report.html")

    print("Enrollment processing complete. Report generated.")


if __name__ == "__main__":
    run_legacy_enrollment()
