from infrastructure.sqlite_enrollment_repository import EnrollmentRepository
from infrastructure.csv_enrollment_reader import read_enrollment_rows
from infrastructure.console_email_notifier import send_notification
from domain.enrollment_rules import determine_status
from domain.notifications import build_notification_message
from presentation.html_report_builder import HtmlReportBuilder

# Application configuration -- not a business rule, so it lives here in
# the composition root rather than in domain/.
DB_PATH = "university_enrollment.db"
CSV_PATH = "students.csv"


def run_legacy_enrollment():
    """Wire the domain, infrastructure, and presentation layers together
    to reproduce the legacy enrollment run end to end."""
    repository = EnrollmentRepository(DB_PATH)
    repository.create_schema()

    report_builder = HtmlReportBuilder()
    report_builder.start()

    rows = read_enrollment_rows(CSV_PATH)
    if rows is None:
        print("ERROR: CSV file not found!")
        return

    for student_id, student_name, course_code, credits, has_prereqs, override_code in rows:
        current_credits = repository.get_current_enrolled_credits(student_id)
        status = determine_status(current_credits, credits, has_prereqs, override_code)

        message = build_notification_message(student_name, course_code, status)
        send_notification(message)

        repository.save_result(student_id, student_name, course_code, credits, status)
        report_builder.add_result(student_id, student_name, course_code, status)

    repository.commit()
    repository.close()

    report_builder.write("enrollment_report.html")

    print("Enrollment processing complete. Report generated.")


if __name__ == "__main__":
    run_legacy_enrollment()
