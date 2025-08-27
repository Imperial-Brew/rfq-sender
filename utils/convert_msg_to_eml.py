import os
import sys
import argparse
import mimetypes
from email.message import EmailMessage
from email.utils import make_msgid
import extract_msg

DEFAULT_SRC = r"C:\Users\drab.dustin\PycharmProjects\rfq-sender\data_raw\RFQ responses\inbox_msg"
DEFAULT_DEST = r"C:\Users\drab.dustin\PycharmProjects\rfq-sender\data_raw\RFQ responses\inbox_eml"


def _norm_addrs(val: str) -> str:
    """Normalize address list strings (MSG often uses ';' as a separator)."""
    if not val:
        return ""
    # Split on ';' or ',' and re-join with ', '
    parts = [p.strip() for p in val.replace(";", ",").split(",")]
    parts = [p for p in parts if p]
    return ", ".join(parts)


def _ensure_str(value, encodings=("utf-8", "cp1252", "latin-1")) -> str:
    """Return a string from possibly-bytes value using best-effort decoding.
    - None -> ""
    - str -> as-is
    - bytes -> try utf-8, then cp1252, then latin-1; replace errors.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        b = bytes(value)
        for enc in encodings:
            try:
                return b.decode(enc)
            except Exception:
                continue
        # Fallback with replacement if all fail
        return b.decode(encodings[0], errors="replace")
    # Fallback: coerce to string
    return str(value)


def convert_msg_to_email(msg_path: str) -> EmailMessage:
    m = extract_msg.Message(msg_path)
    em = EmailMessage()

    # Basic headers
    if getattr(m, "sender", None):
        em["From"] = m.sender
    if getattr(m, "to", None):
        em["To"] = _norm_addrs(m.to)
    if getattr(m, "cc", None):
        em["Cc"] = _norm_addrs(m.cc)
    # Some MSGs have bcc, but typically clients drop it when forwarding; include if present
    if getattr(m, "bcc", None):
        em["Bcc"] = _norm_addrs(m.bcc)
    if getattr(m, "date", None):
        em["Date"] = m.date
    if getattr(m, "subject", None):
        em["Subject"] = m.subject

    # Provide a Message-ID if none exists (optional but helpful)
    if "Message-ID" not in em:
        em["Message-ID"] = make_msgid()

    # Body handling: prefer plain text, add HTML alternative when available
    raw_text = getattr(m, "body", None)
    raw_html = getattr(m, "htmlBody", None)

    text_body = _ensure_str(raw_text)
    html_body = _ensure_str(raw_html) if raw_html is not None else None

    if text_body:
        em.set_content(text_body, subtype="plain", charset="utf-8")
        if html_body:
            em.add_alternative(html_body, subtype="html", charset="utf-8")
    elif html_body:
        # Only HTML available
        em.set_content(html_body, subtype="html", charset="utf-8")
    else:
        # No body found at all
        em.set_content("")

    # Attachments
    for att in getattr(m, "attachments", []) or []:
        filename = getattr(att, "longFilename", None) or getattr(att, "shortFilename", None) or "attachment"
        data = getattr(att, "data", None)
        if data is None:
            continue
        guessed, _ = mimetypes.guess_type(filename)
        maintype = "application"
        subtype = "octet-stream"
        if guessed:
            try:
                maintype, subtype = guessed.split("/", 1)
            except ValueError:
                pass
        em.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    return em


essential_description = (
    "Convert Outlook .msg emails in a source folder to RFC 5322 .eml files in a destination folder."
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=essential_description)
    parser.add_argument("--src", default=DEFAULT_SRC, help="Source folder containing .msg files")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Destination folder to write .eml files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .eml files if present")
    args = parser.parse_args(argv)

    src = args.src
    dest = args.dest
    os.makedirs(dest, exist_ok=True)

    if not os.path.isdir(src):
        print(f"Source folder does not exist: {src}", file=sys.stderr)
        return 2

    converted = 0
    skipped = 0
    failed = 0

    for name in os.listdir(src):
        if not name.lower().endswith(".msg"):
            continue
        msg_path = os.path.join(src, name)
        out_name = os.path.splitext(name)[0] + ".eml"
        out_path = os.path.join(dest, out_name)

        if os.path.exists(out_path) and not args.overwrite:
            skipped += 1
            print(f"Skip (exists): {out_name}")
            continue

        try:
            em = convert_msg_to_email(msg_path)
            with open(out_path, "wb") as f:
                f.write(em.as_bytes())
            converted += 1
            print(f"Converted: {name} → {out_path}")
        except Exception as e:
            failed += 1
            print(f"Failed {name}: {e}", file=sys.stderr)

    print(f"Done. Converted={converted}, Skipped={skipped}, Failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
