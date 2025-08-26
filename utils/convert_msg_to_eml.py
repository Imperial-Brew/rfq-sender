import os, extract_msg
from email.message import EmailMessage

src  = r"C:\Users\drab.dustin\PycharmProjects\rfq-sender\data_raw\RFQ responses\inbox_msg"
dest = r"C:\Users\drab.dustin\PycharmProjects\rfq-sender\data_raw\RFQ responses\inbox_eml"
os.makedirs(dest, exist_ok=True)

for name in os.listdir(src):
    if not name.lower().endswith(".msg"):
        continue
    path = os.path.join(src, name)
    try:
        m = extract_msg.Message(path)
        em = EmailMessage()
        if m.sender:   em["From"] = m.sender
        if m.to:       em["To"] = m.to
        if m.cc:       em["Cc"] = m.cc
        if m.date:     em["Date"] = m.date
        if m.subject:  em["Subject"] = m.subject

        body = m.body if m.body else (m.htmlBody or "")
        if m.body:
            em.set_content(m.body)
            if m.htmlBody:
                em.add_alternative(m.htmlBody, subtype="html")
        else:
            em.set_content(m.htmlBody or "")

        for att in m.attachments:
            em.add_attachment(
                att.data,
                maintype="application",
                subtype="octet-stream",
                filename=att.longFilename or att.shortFilename
            )

        outpath = os.path.join(dest, os.path.splitext(name)[0] + ".eml")
        with open(outpath, "wb") as f:
            f.write(em.as_bytes())
        print(f"Converted: {name} → {outpath}")
    except Exception as e:
        print(f"Failed {name}: {e}")
