import sqlite3
import os
import csv
from datetime import datetime

# HARDCODED GLOBALS (Smell: Global State / Immobility)
DB_PATH = "university_enrollment.db"
CSV_PATH = "students.csv"
MAX_CREDITS = 18

def run_legacy_enrollment():
    # 1. DATABASE SETUP (Smell: Infrastructure mixed with execution)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS enrollments 
                      (student_id TEXT, student_name TEXT, course_code TEXT, credits INTEGER, status TEXT)''')
    
    # 2. HTML REPORT SETUP (Smell: Presentation mixed with logic)
    html_report = f"<html><body><h1>Enrollment Run: {datetime.now()}</h1><table border='1'>"
    html_report += "<tr><th>ID</th><th>Name</th><th>Course</th><th>Status</th></tr>"
    
    # 3. FILE I/O (Smell: Brittle error handling)
    if not os.path.exists(CSV_PATH):
        print("ERROR: CSV file not found!")
        return

    with open(CSV_PATH, 'r') as file:
        reader = csv.reader(file)
        next(reader) # Skip header
        
        # 4. THE GOD LOOP (Smell: Doing everything at once)
        for row in reader:
            student_id = row[0]
            student_name = row[1]
            course_code = row[2]
            credits = int(row[3])
            has_prereqs = row[4].strip().lower() == 'true'
            override_code = row[5]

            status = "PENDING"
            
            # 5. BUSINESS LOGIC (Smell: Deep nesting and magic strings)
            # Check if student already has too many credits
            cursor.execute("SELECT SUM(credits) FROM enrollments WHERE student_id=? AND status='ENROLLED'", (student_id,))
            result = cursor.fetchone()[0]
            current_credits = result if result else 0

            if current_credits + credits > MAX_CREDITS:
                status = "FAILED - CREDIT LIMIT EXCEEDED"
                # SIMULATED EMAIL (Smell: Side effects hidden in business logic)
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

            # 6. DATABASE EXECUTION (Smell: DB calls inside the loop)
            cursor.execute("INSERT INTO enrollments VALUES (?, ?, ?, ?, ?)", 
                           (student_id, student_name, course_code, credits, status))
            
            # 7. HTML GENERATION (Smell: String concatenation for UI)
            if "FAILED" in status:
                html_report += f"<tr style='color:red;'><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"
            else:
                html_report += f"<tr><td>{student_id}</td><td>{student_name}</td><td>{course_code}</td><td>{status}</td></tr>"

    # 8. TEARDOWN AND SAVING
    conn.commit()
    conn.close()
    
    html_report += "</table></body></html>"
    
    with open("enrollment_report.html", "w") as report_file:
        report_file.write(html_report)
        
    print("Enrollment processing complete. Report generated.")

if __name__ == "__main__":
    run_legacy_enrollment()