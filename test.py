import pyodbc
import json

# your existing connection
conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=ATH-SQL;"
    "DATABASE=M2MDATA01;"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT v.FVENDNO, v.FCOMPANY, v.FCITY, v.FSTATE, 
                    v.FCEMAIL, v.FCSTATUS
    FROM APVEND v
    JOIN POMAST m ON m.FVENDNO = v.FVENDNO
    JOIN POITEM i ON i.FPONO = m.FPONO
    JOIN JODRTG r ON i.FJOKEY = r.FJOBNO
        AND i.FJOOPNO = r.FOPERNO
        AND r.FPRO_ID LIKE 'SUB-%'
    WHERE v.FCSTATUS = 'A'
        AND m.FSTATUS != 'Cancelled'
""")

m2m_vendors = cursor.fetchall()

# Load existing consolidated json for any supplements you already have
try:
    with open("config/vendors.consolidated-.json", "r") as f:
        existing = json.load(f).get("vendors", [])
except FileNotFoundError:
    existing = []

# Build merged records
vendors_out = []
for v in m2m_vendors:
    vendor_id = v.FVENDNO.strip()

    supplement = next(
        (x for x in existing if x.get("vendor_number") == vendor_id),
        {}
    )
    # debug - remove after fixed
    if vendor_id in ["001354", "001410", "000766"]:
        print(f"\n--- DEBUG {vendor_id} ---")
        print(f"supplement found: {bool(supplement)}")
        print(f"supplement keys: {supplement.keys() if supplement else 'none'}")
        print(f"processes value: {supplement.get('processes')}")
    city = v.FCITY.strip().rstrip(',')
    state = v.FSTATE.strip()
    location = f"{city}, {state}" if city and state else city or state

    contacts = supplement.get("contacts") or [{
        "name": "Purchasing Contact",
        "email": v.FCEMAIL.strip(),
        "role": "purchasing",
        "receives_rfq": True,
        "active": True
    }]

    vendors_out.append({
        "vendor_id": vendor_id,
        "vendor_name": v.FCOMPANY.strip(),
        "location": location,
        "m2m_email": v.FCEMAIL.strip(),
        "default_contact": supplement.get("default_contact", v.FCEMAIL.strip()),
        "contacts": supplement.get("contacts", [{
            "name": "Purchasing Contact",
            "email": v.FCEMAIL.strip(),
            "role": "purchasing",
            "receives_rfq": True,
            "active": True
        }]),
        "processes": supplement.get("processes", []),
        "notes": supplement.get("notes") or "",
        "rating": supplement.get("rating", None),
        "active": True
    })

# Write output
output = {"vendors": vendors_out}
with open("vendors.consolidated.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Written {len(vendors_out)} vendors to vendors.consolidated.json")

# debug the actual values being compared
old_numbers = [x.get("vendor_number") for x in existing]
print(repr(old_numbers[0]))  # show exact bytes of first entry
print(repr(vendor_id))       # show exact bytes from M2M
print("001354" in old_numbers)  # direct check