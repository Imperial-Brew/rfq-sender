# RFQ Sender - System Flow (with Status Tracking)

## Stage 1: Queue Intake

### Manual Entry (✅ Working)

* RFQs added via editable CSV (Queue.csv)
* Risk of:

  * Typos
  * Duplicates
  * Field name drift

### Auto-Populate from Paperless (🔜 Planned)

* Direct import from Paperless API
* Controlled and consistent data

### Queue Form Interface (🧩 Planned)

* Optional GUI or CLI entry form
* Enforces validation:

  * No duplicate `quote_id`
  * Strict field names (e.g., `qty`, `part_number`, `spec`, etc.)

---

## Stage 2: Vendor Matching

### Match by Spec (✅ Working)

* Uses `vendor_options.yaml`
* Primary method for matching

### Fallback: Match by Process (✅ Working)

* Used when no matching spec is found
* Matches string or dictionary `name` values

### Extend to Material/Hardware Vendors (🔜 Planned)

* Expand logic to support other vendor types
* May require new format or tags in YAML

---

## Stage 3: Email Draft Creation

### Template-Based Email (✅ Working)

* Jinja2 support with fallback text template

### File Attachment Logic (✅ Working)

* Scans folders, matches part# in filenames
* Skips Excel/Word docs
* Warns if missing files

### Outlook Draft Generation (✅ Working)

* One draft per vendor-process
* Uses saved HTML signature

### Structured Table Insertion (✅ Working)

* Adds quote table (HTML or CSV)
* Based on `Sample_Table(Empty)-OS.csv`

---

## Stage 4: RFQ Response Handling

### Vendor Replies (✅ In Use)

* Email replies from vendors now arriving

### Manual Logging (🧩 Partial)

* Ad hoc tracking only
* No parsing or structured import

### Automated Parsing (🔜 High Priority)

* Detect line-item data in email responses
* Normalize and log to "Received Log"

### Quote Tracker / History Log (🧩 Planned)

* Archive all sent/received RFQs
* Include turnaround times, wins/losses

---

## Stage 5: Logging & Reporting

### RFQ Log (✅ Working)

* `logs.csv` tracks draft generation per vendor-process

### Queue Log (🔜 Planned)

* Stores a snapshot of every queue entry processed

### Response Log (🔜 Planned)

* Structured table of all quote responses received

### Retry/Error Log (🧩 Future)

* Tracks failed drafts, missing paths, or skipped vendors

---

## Stage 6: Scalability & Expansion

### Additional Vendor Types (🔜 In Planning)

* Materials
* Hardware

### GUI/Web Interface (🧩 Future)

* Visual queue review + status tracking

### Approval & Locking Mechanisms (🧩 Future)

* Lock queue after send
* Log who submitted/approved

### Quote Comparison / Analytics (🧩 Long-Term)

* Visual dashboard (e.g., CSV or Power BI)
* Vendor scoring & historical pricing
