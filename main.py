import os
import csv
from datetime import datetime

from infrastructure.sqlite_enrollment_repository import EnrollmentRepository

# HARDCODED GLOBALS (unchanged from legacy_enrollment_processor.py)
DB_PATH = "university_enrollment.db"
CSV_PATH = "students.csv"
MAX_CREDITS = 18


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

    # 3. FILE I/O (unchanged)
    if not os.path.exists(CSV_PATH):
        print("ERROR: CSV file not found!")
        return

    with open(CSV_PATH, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header

        # 4. THE GOD LOOP (unchanged, except DB calls now go through the repository)
        for row in reader:
            student_id = row[0]
            student_name = row[1]
            course_code = row[2]
            credits = int(row[3])
            has_prereqs = row[4].strip().lower() == 'true'
            override_code = row[5]

            status = "PENDING"

            # 5. BUSINESS LOGIC (unchanged)
            # Check if student already has too many credits
            current_credits = repository.get_current_enrolled_credits(student_id)

            if current_credits + credits > MAX_CREDITS:
                status = "FAILED - CREDIT LIMIT EXCEEDED"
                # SIMULATED EMAIL (unchanged)
                print(f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Credit limit).")
            else:
                if has_prereqs:
                    status = "ENROLLED"
                    print(f"SENDING EMAIL TO: {student_name} -> Successfully enrolled in {course_code}.")
                else:
                    if override_code == "DEAN_APPROVED":
                        status = "ENROLLED (OVERRIDE)"
                        print(f"SENDING EMAIL TO: {student_name} -> Enrolled in {course_code} with Dean override.")
                    else:
                        status = "FAILED - MISSING PREREQS"
                        print(f"SENDING EMAIL TO: {student_name} -> Registration failed for {course_code} (Missing Prereqs).")

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
