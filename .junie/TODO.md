RFQ Sender - Development To-Do List

🔴 High Priority

1. Response Parsing & Logging

Parse incoming email replies

Extract per-line price, lead time, vendor notes

Normalize into structured "Received Log"

Optional: Flag mismatched specs/qtys

2. Paperless API Queue Import

Authenticate and pull active quotes

Normalize part#, qty, process, spec, file path

Merge into queue (with duplication checks)

🟠 Medium Priority

3. Queue Entry Form with Validation

GUI or CLI entry system

Enforce field names and types

Reject invalid entries or dupes

4. Logging System Expansion

Add "Queue Log" for all processed entries

Add "Response Log" for parsed replies

Future: Add "History Log" with status rollups

5. Material and Hardware Vendor Support

Extend vendor_options.yaml format

Update filter logic to support new vendor types

🟢 Low Priority / Future

6. GUI or Web Interface

View queue, drafts, logs

Drag & drop uploads

Email send approvals (optional)

7. Quote Comparison Tool

Compare quotes received for same line

Auto-highlight lowest cost / shortest lead

Export to report or summary view

8. Vendor Preference Profiles

Store per-vendor:

Preferred format (Excel, inline)

Response method (reply, portal)

Grouped or one-process RFQs

9. CUI/ITAR Compliance Enhancements

Detect protected files (e.g., based on folder or tag)

Auto-generate Box/secure links

Add compliance notices to body text

