# Box Integration for RFQ Sender

## Implementation Summary

The Box integration has been successfully implemented to handle file attachments with enhanced features for security, performance, and user experience:

1. **Core Components**:
   - `BoxIntegration` class in `box_integration.py` handles Box API operations
   - `create_draft_email` function in `email_from_list.py` uses Box for file sharing
   - Test scripts verify functionality

2. **Credentials Management**:
   - Box client ID and client secret are stored in `scripts/0__config.json`
   - Box access token and refresh token are stored in environment variables (`.env` file)
   - Tokens are refreshed automatically and stored in environment variables

3. **Enhanced Security**:
   - Password protection for shared links (optional)
   - Link expiration functionality (configurable in days)
   - Detailed logging of security settings

4. **Improved File Upload Performance**:
   - Chunked uploads for large files (configurable chunk size)
   - Timeout parameters to control upload duration
   - Retry logic with exponential backoff for failed operations
   - Progress reporting for large file uploads

5. **Enhanced User Experience**:
   - Prominent Box share link display in emails
   - Styled HTML link with visual cues and clear call-to-action
   - Formatted plain text link with clear instructions
   - All files are uploaded to Box for consistency

6. **Workflow**:
   - All files are uploaded to Box instead of being attached directly to emails
   - A Box share link is included prominently in the email body
   - Detailed information about uploaded files is included in the email

## Usage

### Creating a Share Link with JWT Authentication

```python
from scripts.box_integration import BoxIntegration

# Initialize Box integration with JWT authentication
# The JWT credentials are loaded from scripts/0__config.json
box = BoxIntegration()

# Create a folder
folder = box.create_folder("My RFQ Files")

# Upload files with performance options
uploaded_files = box.upload_files(
    ["file1.pdf", "file2.pdf"], 
    folder,
    timeout=600,        # 10 minutes timeout
    max_retries=5,      # Retry up to 5 times
    chunk_size=16777216 # 16MB chunks
)

# Create a share link with security options
share_link = box.create_share_link(
    folder,
    access="open",      # "open", "company", or "collaborators"
    password="SecureRFQ123",  # Optional password protection
    expire_days=30      # Link expires after 30 days
)
```

### Email Template Enhancements

The Box share link is now prominently displayed in emails:

- **HTML Emails**: 
  - Styled container with background color and border
  - Folder icon and clear heading
  - Prominent link with button-like styling
  - Clear call-to-action text

- **Plain Text Emails**:
  - ASCII-art box around the link section
  - Clear heading in all caps
  - Double arrows pointing to the link
  - Clear instructions for recipients

## Authentication Requirements

The Box integration now uses JWT authentication for more secure and reliable server-to-server communication. This method eliminates the need for refresh tokens and provides better security.

### JWT Authentication Setup

For the Box integration to work properly with JWT authentication, you need to set up the following:

1. **Box Application Settings** (in `scripts/0__config.json`):
   - The application must be configured as a "Custom App" with "Server Authentication (with JWT)" access type
   - The config file should include:
     - `boxAppSettings.clientID`: Your Box application client ID
     - `boxAppSettings.clientSecret`: Your Box application client secret
     - `boxAppSettings.appAuth.publicKeyID`: The public key ID
     - `boxAppSettings.appAuth.privateKey`: The encrypted private key
     - `boxAppSettings.appAuth.passphrase`: The passphrase to decrypt the private key
     - `enterpriseID`: Your Box enterprise ID

2. **Required Dependencies**:
   - `cryptography`: For handling encryption operations
   - `PyJWT`: For JWT token generation and validation

### Enterprise Authorization

The Box application must be authorized by your enterprise admin in the Box Admin Console:

1. **Admin Authorization**:
   - Log in to the [Box Admin Console](https://app.box.com/master)
   - Navigate to Enterprise Settings > Apps
   - Find your application under the "Custom Applications" section
   - Click "Authorize" to allow the application to access your enterprise

2. **Application Scopes**:
   - Ensure your application has the necessary scopes:
     - `manage_enterprise` (if accessing enterprise-wide features)
     - `manage_app_users` (if creating/managing app users)
     - `manage_managed_users` (if managing enterprise users)
     - `manage_groups` (if working with groups)

### How to Obtain Box JWT Credentials

1. **Create a Box Developer Account**:
   - Go to [Box Developer Console](https://developer.box.com/) and sign up or log in
   - Create a new Custom App with "Server Authentication (with JWT)" access type

2. **Configure Your App**:
   - Set the required permissions (read/write for files and folders)
   - Under "Configuration" tab, click "Generate a Public/Private Keypair"
   - This will download a JSON file with all the necessary credentials

3. **Update Your Configuration**:
   - Copy the contents of the downloaded JSON file to `scripts/0__config.json`
   - Ensure this file is added to `.gitignore` to prevent committing sensitive credentials

## Troubleshooting

### Common Issues

1. **"This app is not authorized by the enterprise admin"**:
   - This error occurs when your Box application hasn't been authorized by the enterprise admin
   - Follow the steps in the "Enterprise Authorization" section above to authorize your application
   - Ensure the application is approved in the Box Admin Console under Enterprise Settings > Apps

2. **"Box JWT authentication error: Issue with JWT credentials"**:
   - Verify that your `0__config.json` file contains valid JWT credentials
   - Check that the private key and passphrase are correct
   - Ensure the public key ID matches the one in your Box Developer Console
   - Try generating a new keypair if issues persist

3. **"The grant type is unauthorized for this client_id"**:
   - This error occurs when the Box SDK tries to use OAuth2 authentication with a client ID that's configured for JWT authentication
   - Remove or comment out the `BOX_ACCESS_TOKEN` and `BOX_REFRESH_TOKEN` environment variables in the `.env` file
   - The Box SDK will then only use JWT authentication with the credentials in the `0__config.json` file
   - JWT authentication is the recommended method for server-to-server authentication

4. **"Failed to create Box folder" or "Failed to upload file to Box"**:
   - Check your Box credentials in `0__config.json`
   - Verify that your Box application has sufficient permissions
   - Ensure the application is authorized by the enterprise admin
   - Check your network connection

5. **"Failed to create Box share link"**:
   - Verify that your Box account has sharing permissions
   - Check if there are any sharing restrictions on your Box account
   - Ensure your application has the necessary scopes for sharing

### JWT Authentication Advantages

Unlike OAuth2 with refresh tokens, JWT authentication:

1. **No Token Expiration Issues**: JWT tokens are generated on-demand and don't require refresh tokens
2. **Simplified Configuration**: All authentication details are in a single config file
3. **Better Security**: Private key can be encrypted with a passphrase
4. **Server-to-Server**: Designed specifically for server-to-server authentication without user interaction

## Future Recommendations

1. **Configuration Improvements**:
   - Add Box-specific settings to `email.yml`
   - Make all threshold values configurable through config files

2. **Additional Security Enhancements**:
   - Implement IP restriction for shared links
   - Add watermarking for sensitive documents
   - Implement Box Shield for advanced security (requires Enterprise plan)

3. **User Experience Improvements**:
   - Add a web interface for monitoring upload progress
   - Implement email notifications when files are accessed
   - Add preview thumbnails in emails for uploaded files

4. **Authentication Improvements**:
   - Implement automatic JWT token caching for performance
   - Add support for application user management
   - Create a web interface for managing Box credentials and monitoring usage

The implementation is complete and working as expected, following the project's style guidelines and providing a seamless, secure, and efficient experience for users.