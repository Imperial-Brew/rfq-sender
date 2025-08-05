📂 RFQ Folder Structure SOP: Box Hybrid Model (For Junie)

✨ Overview:

To streamline vendor quoting, we are adopting a hybrid folder structure. All RFQ documentation will be organized first by quote or order number (qt/so #), then by part number. Vendor-specific folders will be generated inside a subfolder and shared via Box links.

🔧 Folder Layout Example

/Box/FinishingRFQs/QT57267/
├── PN-001/
├── PN-002/
├── PN-003/
├── PN-004/
├── PN-005/
└── vendor_links/
    ├── HeatTreatCo/
    ├── AnodizePro/
    └── NickelWorks/

✅ Instructions

1. Create Master RFQ Folder

Navigate to: /Box/FinishingRFQs/

Create a folder named using the qt/so #: QT57267

2. Add Part Folders

Inside /QT57267/, create one folder per part number: e.g. PN-001, PN-002, etc.

Inside each part folder, add:

Customer drawing files (PDF, DXF, etc.)

Callouts or notes (TXT, screenshots, etc.)

Internal RFQ documentation (optional)

Note: Avoid duplicating files. Each part should only exist once.

3. Create Vendor Link Folder

Inside /QT57267/, create a folder: vendor_links

Inside vendor_links, create one folder per vendor:

e.g., HeatTreatCo, NickelWorks, etc.

4. Populate Vendor Subfolders

For each vendor, only include folders for the parts and processes they are quoting.

Do not include unrelated parts.

You may copy files or create shortcuts/symlinks (preferred to reduce duplication).

5. Share Vendor Folder

Right-click the vendor's folder inside vendor_links.

Generate a Box share link.

Set expiration and password if needed.

Include this link in the RFQ email to the vendor.

📊 Best Practices

Keep all part folders standardized by part number.

Always use the RFQ tracking sheet or Dustin's app to determine which vendors need which parts.

Label vendor folders consistently (no underscores, avoid special characters).

🚫 Avoid

Do not create one-off folders per vendor in the root.

Do not duplicate entire part folders across vendors.

Do not share entire /QT####/ parent folder with vendors.

This structure supports automation, easy auditing, and minimal duplication. When in doubt, ask Dustin or refer to the RFQ record in Paperless.

