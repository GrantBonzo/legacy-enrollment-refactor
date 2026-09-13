# Legacy Enrollment Processor Architecture

## 1. Current Execution Flow

1. The script is invoked via `python legacy_enrollment_processor.py`, which calls `run_legacy_enrollment()` (`legacy_enrollment_processor.py:85-86`).
2. A SQLite connection is opened against the hardcoded path `university_enrollment.db` (`DB_PATH`, line 7, 13), and a cursor is created (line 14).
3. The `enrollments` table is created if it does not already exist, with columns `student_id, student_name, course_code, credits, status` (lines 15-16).
4. An HTML string buffer (`html_report`) is initialized in memory with an opening `<html>` header, timestamp, and table header row (lines 19-20).
5. The program checks for the existence of `students.csv` (`CSV_PATH`, line 8). If the file is missing, it prints an error and returns immediately, leaving the (already-created) empty database table and no report file behind (lines 23-25).
6. The CSV file is opened and read row by row via `csv.reader`, skipping the header row (lines 27-29).
7. For each data row (the "god loop", lines 32-72):
   a. Fields are unpacked positionally into `student_id`, `student_name`, `course_code`, `credits`, `has_prereqs`, `override_code` (lines 33-38).
   b. The database is queried synchronously to sum the student's currently `ENROLLED` credits (lines 44-46).
   c. Business rules are evaluated in nested `if/else` blocks to determine enrollment `status`:
      - If adding the new course would exceed `MAX_CREDITS` (18), status becomes `FAILED - CREDIT LIMIT EXCEEDED` (lines 48-49).
      - Otherwise, if prerequisites are met, status becomes `ENROLLED` (lines 53-54).
      - Otherwise, if a Dean override code (`DEAN_APPROVED`) is present, status becomes `ENROLLED (OVERRIDE)` (lines 57-58).
      - Otherwise, status becomes `FAILED - MISSING PREREQS` (lines 60-61).
   d. For every branch, a simulated email notification is printed to the console describing the outcome (lines 51, 55, 59, 62).
   e. The row's result is immediately inserted into the `enrollments` table via a per-row `INSERT` (lines 65-66).
   f. An HTML `<tr>` row is appended to the in-memory report buffer, styled red if the status contains `"FAILED"` (lines 69-72).
8. After all rows are processed, the database transaction is committed and the connection is closed (lines 75-76).
9. The HTML buffer is closed out with closing tags (line 78) and written to `enrollment_report.html` on disk (lines 80-81).
10. A final completion message is printed to the console (line 83).

## 2. Responsibilities Currently Contained in the Monolith

- **Infrastructure/connection management**: opening and closing a SQLite connection, schema creation (`CREATE TABLE IF NOT EXISTS`).
- **File I/O**: checking for and reading a CSV file; writing an HTML file to disk.
- **Data parsing/mapping**: converting raw CSV string fields into typed values (e.g., `int(row[3])`, boolean parsing of `row[4]`).
- **Persistence/querying**: running a `SELECT SUM(...)` query per student and an `INSERT` per enrollment record.
- **Business/domain rules**: credit-limit enforcement (18-credit cap), prerequisite checking, Dean override logic, and status determination.
- **Notification/side effects**: simulating email sends via `print()` statements embedded directly in the branching logic.
- **Presentation/report generation**: building an HTML document via string concatenation, including conditional styling (red rows for failures).
- **Orchestration/control flow**: the single function sequences all of the above steps in one linear procedure with no internal boundaries.
- **Error handling**: a single, coarse check for a missing CSV file, with no handling for malformed rows, DB errors, or write failures.

## 3. Architectural and Code Smells

### Smell 1: God Function / Single Responsibility Violation
- **Location**: The entire body of `run_legacy_enrollment()`, `legacy_enrollment_processor.py:11-83`.
- **Evidence**: One function performs database setup, file existence checking, CSV parsing, business rule evaluation, database writes, console-based "email" notification, and HTML report generation — all in a single unbroken block, including within the same `for` loop (lines 32-72).
- **Why it is problematic**: The function cannot be tested, reused, or reasoned about in isolation. A change to how HTML is rendered risks breaking business logic; a change to the credit-limit rule requires touching a function that also knows about SQLite and HTML strings. There is no unit of code that represents "the enrollment decision" independent of its storage or presentation.
- **Architectural consequence**: Domain logic (credit limits, prerequisites, overrides), infrastructure/data access (SQLite reads/writes), and presentation (HTML/console output) are all fused into one procedure, meaning none of the three can vary independently.
- **Direction of eventual change**: Decompose the function into distinct layers/units — a domain service that evaluates enrollment eligibility given inputs, a repository/data-access component that owns all SQLite interaction, and a presentation/reporting component that owns HTML generation — coordinated by a thin orchestrator, without changing observable output.

### Smell 2: Business Logic Coupled to Persistence (Inline Query-in-Loop)
- **Location**: `legacy_enrollment_processor.py:44-46` inside the per-row loop, immediately feeding the credit-limit decision at line 48.
- **Evidence**: `cursor.execute("SELECT SUM(credits) FROM enrollments WHERE student_id=? AND status='ENROLLED'", (student_id,))` is executed once per CSV row, and its result is used directly as an input to the `if current_credits + credits > MAX_CREDITS` business rule on the very next lines.
- **Why it is problematic**: The domain rule ("a student may not exceed 18 enrolled credits") cannot be evaluated, tested, or reasoned about without a live SQLite connection and a populated `enrollments` table. This also means the rule's correctness is entangled with the loop's execution order (a student's own earlier rows in the same run affect later rows within the same file), and testing the rule requires standing up a real database.
- **Architectural responsibility incorrectly combined**: Domain/business rule evaluation is combined with infrastructure data access (SQL querying).
- **Direction of eventual change**: Have the persistence layer expose a repository method (e.g., "get current enrolled credits for student") whose result is passed as a plain value into a pure domain function that decides eligibility, so the rule itself has no knowledge of SQL or SQLite.

### Smell 3: Presentation Logic Embedded in the Processing Loop (HTML String Building)
- **Location**: `legacy_enrollment_processor.py:19-20` (report header) and `69-72` (per-row HTML) inside the same loop as business logic and database writes.
- **Evidence**: `html_report += f"<tr style='color:red;'>...` is constructed conditionally based on the same `status` variable used for the DB insert and the email print, directly interleaved with those other concerns in the loop body.
- **Why it is problematic**: The report format (HTML, red-highlighting rule, column layout) is hardcoded and mixed with the logic that produces the data it displays. Changing the report format (e.g., to JSON, PDF, or a different HTML template) requires editing the same function that contains the enrollment decision logic and database writes, risking regressions in unrelated concerns. There is also no separation between "the data produced by a run" and "how that data is rendered."
- **Architectural responsibility incorrectly combined**: Presentation/reporting is combined with both domain logic and data-access/orchestration.
- **Direction of eventual change**: Accumulate structured result records (plain data, not HTML) during processing, and hand that collection to a separate presentation/report-generation component responsible solely for rendering it to HTML (or any other format) after processing completes.

### Smell 4 (additional): Hidden Side Effects and Global Hardcoded Configuration
- **Location**: Module-level constants `DB_PATH`, `CSV_PATH`, `MAX_CREDITS` (lines 7-9); `print()`-based "email" side effects at lines 51, 55, 59, 62.
- **Evidence**: File paths and the credit cap are hardcoded module globals rather than parameters or injected configuration; simulated email notifications are fired via bare `print()` calls buried inside conditional branches of the business-rule evaluation, with no abstraction (e.g., a notifier interface) around them.
- **Why it is problematic**: The processing logic cannot run against different data sources, output locations, or credit limits without editing source code. The "notification" side effect is indistinguishable from debug output and cannot be swapped for a real email/SMS integration, disabled in tests, or verified without capturing stdout.
- **Architectural responsibility incorrectly combined**: Configuration/environment concerns and notification/output side effects are combined directly with control flow and business-rule branches.
- **Direction of eventual change**: Externalize configuration (paths, credit limit) as injected parameters, and introduce a notification abstraction (e.g., a port/interface for "notify student of outcome") that the domain layer calls without knowing how notification is actually implemented (console print today, real email later).

## 4. Current Dependencies

- **SQLite**: Directly depended on by the core function itself — `sqlite3.connect`, `cursor.execute`, `cursor.fetchone`, `conn.commit`, and `conn.close` calls are inlined in `run_legacy_enrollment()` (lines 13-16, 44-46, 65-66, 75-76). There is no abstraction layer; the function *is* the data-access code.
- **CSV files**: Directly depended on via `os.path.exists`, `open(CSV_PATH, 'r')`, and `csv.reader` calls inline in the same function (lines 23-29). Row parsing (positional indexing and type coercion) is also done inline, with no separate loader or mapper.
- **HTML generation**: Directly depended on via raw string concatenation (`html_report +=`) built up inside the same loop that performs business logic and database writes, then written to `enrollment_report.html` with a plain `open(...).write(...)` call (lines 19-20, 69-72, 78, 80-81). No templating engine or dedicated rendering component is used.
- **Console/email output**: The "email" notification is simulated entirely via `print()` statements embedded directly in the business-rule branches (lines 51, 55, 59, 62); the final completion message is also a `print()` call (line 83). There is no notification abstraction — console output is the only channel, and it is indistinguishable from ordinary logging.

## 5. Refactoring Constraints

To preserve external behavior during the future Clean Architecture refactor, the following must remain unchanged:

- **Inputs and outputs**: The program must still read from `students.csv` with the same expected column order (`student_id, student_name, course_code, credits, has_prereqs, override_code`) and produce a SQLite database file and an `enrollment_report.html` file with equivalent content.
- **Database schema**: The `enrollments` table structure (`student_id, student_name, course_code, credits, status`) must be preserved so existing data/reports remain compatible.
- **Business rules**: The 18-credit maximum, the prerequisite check, and the `DEAN_APPROVED` override behavior must produce identical enrollment decisions for the same inputs.
- **Status values**: The exact status strings (`ENROLLED`, `ENROLLED (OVERRIDE)`, `FAILED - CREDIT LIMIT EXCEEDED`, `FAILED - MISSING PREREQS`) must be preserved, since they are persisted to the database and rendered in the report.
- **Report format**: The HTML report's structure (table with ID/Name/Course/Status columns, red styling for failed rows, timestamp header) must remain visually/structurally equivalent.
- **Notification behavior**: The simulated email messages printed to the console must retain their existing content and triggering conditions, even if the underlying mechanism is later abstracted.
- **Missing-file behavior**: The behavior when `students.csv` is absent (print an error message and exit without processing) must be preserved unless explicitly revised.
