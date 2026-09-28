import json

with open("config/vendors.consolidated-.json", "r") as f:
    old = json.load(f)

# show vendor_number and processes for any vendor that has processes
for v in old["vendors"]:
    if v.get("processes"):
        print(v["vendor_number"], "|", v["name"], "|", len(v["processes"]), "processes")