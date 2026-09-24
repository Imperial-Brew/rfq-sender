# Changes Needed for streamlit_app/pages/05_send_rfq_emails.py

The file `streamlit_app/pages/05_send_rfq_emails.py` contains multiple instances of SMTP settings that need to be updated to use exchangelib instead. Here are the changes needed:

## 1. Update Import Statements

Add the dotenv import at the top of the file:
```python
from dotenv import load_dotenv
```

## 2. Replace SMTP Settings with Exchange Settings

There are multiple instances of SMTP settings in the file. Each instance needs to be replaced with Exchange settings:

### For the first instance (around line 167):
```python
# Read .env file for Exchange settings
load_dotenv(dotenv_path=parent_dir / ".env")

# Use Exchange settings from environment variables
exchange_settings = {
    "username": os.environ.get("EXCHANGE_USERNAME", ""),
    "from_email": os.environ.get("EXCHANGE_FROM_EMAIL", ""),
    "cc": os.environ.get("EXCHANGE_CC_EMAIL", "")
}
```

### For the second instance (around line 305):
```python
# Read .env file for Exchange settings
load_dotenv(dotenv_path=parent_dir / ".env")

# Use Exchange settings from environment variables
exchange_settings = {
    "username": os.environ.get("EXCHANGE_USERNAME", ""),
    "from_email": os.environ.get("EXCHANGE_FROM_EMAIL", ""),
    "cc": os.environ.get("EXCHANGE_CC_EMAIL", "")
}
```

## 3. Update References to smtp_settings

Replace all references to `smtp_settings` with `exchange_settings`:

- Line 208: `"sender_email": user.get("email", exchange_settings["from_email"]),`
- Line 265: `smtp_settings=exchange_settings`
- Line 346: `"sender_email": user.get("email", exchange_settings["from_email"]),`
- Line 356: `smtp_settings=exchange_settings,`
- Line 449: `smtp_settings=exchange_settings,`

## 4. Remove SMTP Settings UI

The SMTP Settings UI section (around line 411) should be replaced with Exchange Settings UI:

```python
st.markdown("**Exchange Settings**")
st.info("Exchange settings are configured through environment variables. Check the .env file to update these settings.")
```

## Note

These changes align with the updates made to `app.py` and `utils/email.py` to use exchangelib instead of SMTP for sending emails. The exchangelib library is already being used in the backend, and these changes ensure consistent use of exchangelib throughout the application.