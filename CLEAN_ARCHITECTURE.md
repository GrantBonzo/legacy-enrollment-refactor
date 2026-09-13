# Proposed Clean Architecture

This is a design blueprint only. No implementation code is written here, and
`legacy_enrollment_processor.py` is left untouched as the current behavioral
source of truth (see `ARCHITECTURE.md` for the analysis it is based on).

## Directory Structure

```
legacy-enrollment-refactor/
├── legacy_enrollment_processor.py      # unchanged legacy entry point
├── ARCHITECTURE.md
├── CLEAN_ARCHITECTURE.md
├── main.py                             # new composition root / orchestrator
├── domain/
│   ├── __init__.py
│   ├── models.py                       # EnrollmentRequest, EnrollmentResult
│   ├── enrollment_rules.py             # credit limit / prereq / override logic
│   └── notifications.py                # notification message text (pure)
├── infrastructure/
│   ├── __init__.py
│   ├── csv_enrollment_reader.py        # reads students.csv -> EnrollmentRequest
│   ├── sqlite_enrollment_repository.py # schema, credit lookups, inserts
│   └── console_email_notifier.py       # prints the "sent" notification
└── presentation/
    ├── __init__.py
    └── html_report_builder.py          # builds and writes enrollment_report.html
```

Nine new files (three `__init__.py` markers plus six real modules) plus
`main.py` — the smallest split that gives each of the three layers its own
files without introducing frameworks, interfaces-for-their-own-sake, or
speculative abstractions.

## Domain Layer

The domain layer holds only business rules and the plain data shapes they
operate on. It must never import `sqlite3`, `csv`, `os` (for file paths), or
anything that builds HTML or prints to a console.

### `domain/models.py`
- **Responsibility**: Define the plain data shapes that flow between layers.
- **Contents**:
  - `EnrollmentRequest` — one parsed CSV row: `student_id`, `student_name`, `course_code`, `credits`, `has_prereqs`, `override_code`.
  - `EnrollmentResult` — the outcome of processing a request: `student_id`, `student_name`, `course_code`, `credits`, `status`.
- **Should NOT know about**: SQLite, CSV file format/parsing, HTML, or how/whether a notification is sent. These are plain, dependency-free data containers (e.g. `dataclasses`), not database rows or CSV rows.

### `domain/enrollment_rules.py`
- **Responsibility**: Decide the enrollment `status` for a single request, given the student's currently enrolled credits. This is the direct replacement for the nested `if/else` block at `legacy_enrollment_processor.py:48-62`.
- **Contents**:
  - `MAX_CREDITS = 18` and `DEAN_OVERRIDE_CODE = "DEAN_APPROVED"` constants (moved from the legacy module-level globals).
  - `evaluate_enrollment(request: EnrollmentRequest, current_enrolled_credits: int) -> EnrollmentResult` — a pure function reproducing the exact original branching: credit-limit check first, then prerequisites, then Dean override, else missing-prereqs failure. Status strings (`ENROLLED`, `ENROLLED (OVERRIDE)`, `FAILED - CREDIT LIMIT EXCEEDED`, `FAILED - MISSING PREREQS`) are preserved verbatim.
- **Should NOT know about**: Where `current_enrolled_credits` came from (SQLite today, anything else tomorrow), how the result will be stored, displayed, or emailed. It takes a plain integer in and returns a plain `EnrollmentResult` out — fully unit-testable with no database.

### `domain/notifications.py`
- **Responsibility**: Decide *what message* should be communicated for a given result — the text content currently hardcoded inline in each branch (`legacy_enrollment_processor.py:51,55,59,62`). This is business communication content, not a delivery mechanism.
- **Contents**:
  - `build_notification_message(result: EnrollmentResult) -> str` — a pure function mapping an `EnrollmentResult` to the exact original message strings (e.g. `"SENDING EMAIL TO: {name} -> Successfully enrolled in {course}."`).
- **Should NOT know about**: `print()`, sockets, SMTP, or any other transport. It only produces a string; it never sends anything.

## Infrastructure/Data Layer

The infrastructure layer contains every direct dependency on SQLite, the CSV
file format, and the simulated email transport. It knows about domain models
(so it can produce/consume them) but never contains business rules and never
builds HTML.

### `infrastructure/csv_enrollment_reader.py`
- **Responsibility**: Replace `legacy_enrollment_processor.py:23-38` — locate, open, and parse `students.csv` into domain objects.
- **Contents**:
  - `read_enrollment_requests(csv_path: str) -> list[EnrollmentRequest]` — opens the file, skips the header, parses each row (including the same `int(row[3])` and `row[4].strip().lower() == 'true'` conversions), and returns a list of `EnrollmentRequest`.
  - A way to signal "file not found" that preserves the original behavior (e.g. raising `FileNotFoundError`, or returning `None`, for `main.py` to handle identically to the legacy `ERROR: CSV file not found!` message and early return).
- **Should NOT know about**: SQLite, the 18-credit rule, prerequisite/override logic, or HTML — it only turns rows of text into `EnrollmentRequest` objects.

### `infrastructure/sqlite_enrollment_repository.py`
- **Responsibility**: Replace all direct SQLite usage — schema creation (`legacy_enrollment_processor.py:15-16`), the per-student credit sum query (lines 44-46), the per-row insert (lines 65-66), and commit/close (lines 75-76).
- **Contents**:
  - `EnrollmentRepository` class wrapping a `sqlite3` connection, exposing:
    - `__init__(db_path: str)` / connection setup
    - `create_schema() -> None` — the `CREATE TABLE IF NOT EXISTS enrollments ...` statement
    - `get_current_enrolled_credits(student_id: str) -> int` — the `SELECT SUM(credits) ... WHERE status='ENROLLED'` query, returning `0` when there is no result (preserving the `result if result else 0` behavior)
    - `save_result(result: EnrollmentResult) -> None` — the `INSERT INTO enrollments VALUES (...)` call
    - `commit() -> None` / `close() -> None`
- **Should NOT know about**: CSV parsing, the credit-limit/prerequisite/override rules, notification text, or HTML rendering. It only knows how to read and write rows shaped like `EnrollmentResult`/`EnrollmentRequest` fields.

### `infrastructure/console_email_notifier.py`
- **Responsibility**: Replace the `print(f"SENDING EMAIL TO: ...")` side effect (lines 51, 55, 59, 62) with a dedicated notification-sending unit.
- **Contents**:
  - `send_notification(message: str) -> None` — currently just `print(message)`, matching the exact console output of the legacy version, but now swappable later for a real email integration without touching business logic.
- **Should NOT know about**: How the message text was constructed, what the enrollment status means, or any business rule. It only knows how to "deliver" a string it is handed.

## Presentation Layer

The presentation layer owns the shape and rendering of the HTML report. It
knows about domain result data (to display it) but never computes it, never
touches SQLite or CSV, and never decides enrollment outcomes.

### `presentation/html_report_builder.py`
- **Responsibility**: Replace the HTML string-building scattered across `legacy_enrollment_processor.py:19-20, 69-72, 78, 80-81`.
- **Contents**:
  - `HtmlReportBuilder` class (or equivalent small set of functions) with:
    - a way to start a report (header + timestamp, matching `<html><body><h1>Enrollment Run: {datetime.now()}</h1>...`)
    - `add_result(result: EnrollmentResult) -> None` — appends a `<tr>` row, applying the same `style='color:red;'` rule when `"FAILED"` is in `result.status`
    - `render() -> str` — closes out the `</table></body></html>` tags and returns the full HTML string
  - A `write_report(path: str, html: str) -> None` helper (or a method on the same module) that writes the rendered string to `enrollment_report.html`, matching lines 80-81. Kept in this module rather than a separate file since it is a one-line file write directly tied to the HTML it renders, and splitting it out would be an unnecessary abstraction.
- **Should NOT know about**: SQLite, CSV parsing, the credit-limit/prerequisite/override rules, or how notifications are sent. It only knows how to turn a sequence of `EnrollmentResult` objects into an HTML document.

## Application Flow

`main.py` is the composition root: it imports from all three layers, wires
them together, and contains no business rules, SQL, or HTML of its own —
only sequencing, mirroring the legacy control flow step-for-step.

1. `main.py` constructs an `EnrollmentRepository`, calls `create_schema()`.
2. `main.py` starts an `HtmlReportBuilder`.
3. `main.py` calls `csv_enrollment_reader.read_enrollment_requests(CSV_PATH)`. If the file is missing, it prints the same `ERROR: CSV file not found!` message and returns, matching the legacy early exit.
4. For each `EnrollmentRequest` returned:
   a. `main.py` asks the repository for `get_current_enrolled_credits(request.student_id)`.
   b. `main.py` passes the request and that integer into `domain.enrollment_rules.evaluate_enrollment(...)`, receiving an `EnrollmentResult`.
   c. `main.py` passes the result into `domain.notifications.build_notification_message(...)`, then hands the resulting string to `console_email_notifier.send_notification(...)`.
   d. `main.py` calls `repository.save_result(result)`.
   e. `main.py` calls `report_builder.add_result(result)`.
5. After the loop, `main.py` calls `repository.commit()` and `repository.close()`.
6. `main.py` calls `report_builder.render()` and passes the HTML to the write helper to produce `enrollment_report.html`.
7. `main.py` prints the same final `"Enrollment processing complete. Report generated."` message.

Data moves in one direction per step — infrastructure produces domain
objects (`EnrollmentRequest`, credit counts) → domain produces decisions
(`EnrollmentResult`, message text) → infrastructure/presentation consume
those decisions to persist, notify, and render. No layer reaches "backward"
into a layer that depends on it.

## Dependency Rules

- **Domain** depends on nothing else in the application. It has zero imports from `infrastructure/` or `presentation/`, and no imports of `sqlite3`, `csv`, or HTML-building code.
- **Infrastructure** may depend on **Domain** (to accept/return `EnrollmentRequest`/`EnrollmentResult`), but must not depend on **Presentation**.
- **Presentation** may depend on **Domain** (to accept `EnrollmentResult` for rendering), but must not depend on **Infrastructure**.
- **Infrastructure** and **Presentation** must never depend on each other directly — any coordination between "save to DB" and "render to HTML" happens only through `main.py`.
- **`main.py`** (the composition root) is the only module allowed to depend on all three layers simultaneously; it exists solely to wire them together in the correct order.

This keeps the dependency arrows pointing inward toward the domain, per
Clean Architecture: outer layers (infrastructure, presentation) know about
the domain's data shapes and call into its rule functions, but the domain
never knows that SQLite, CSV files, or HTML exist.

## Behavior Preservation

The refactor must produce identical externally observable behavior to
`legacy_enrollment_processor.py`:

- Same CSV input format and column order (`student_id, student_name, course_code, credits, has_prereqs, override_code`), including the header-row skip.
- Same SQLite schema (`enrollments` table with `student_id, student_name, course_code, credits, status` columns) and same database file name.
- Same credit-limit threshold (18) and the same "check current `ENROLLED` sum, then compare with the new course's credits" logic.
- Same prerequisite check and same `DEAN_APPROVED` override code and behavior.
- Same exact status strings: `ENROLLED`, `ENROLLED (OVERRIDE)`, `FAILED - CREDIT LIMIT EXCEEDED`, `FAILED - MISSING PREREQS`.
- Same simulated email message text and same triggering conditions, printed to the console in the same per-row order.
- Same HTML report structure and content: title/timestamp header, table columns (ID, Name, Course, Status), and red styling for any row whose status contains `"FAILED"`.
- Same missing-file behavior: printing `ERROR: CSV file not found!` and exiting without processing when `students.csv` is absent.
- Same final console message: `"Enrollment processing complete. Report generated."`
- Same output file names: `university_enrollment.db` and `enrollment_report.html`.

No implementation has been written yet; this document defines the target
module boundaries the future refactor will implement against.
