User Authentication Implementation Tasklist
This tasklist outlines the steps needed to implement full user authentication with 24-hour session persistence in the RFQ Sender application.

1. User Data Structure Enhancement
Update users.yaml schema to include authentication fields:
Add password_hash field (using bcrypt)
Add last_login timestamp field
Add session_token field (optional)
Create a script to migrate existing users to new schema
Implement password hashing utility functions in utils/auth.py
2. Authentication Backend
Enhance utils/auth.py with new functions:
hash_password(password) - Generate bcrypt hash
verify_password(plain_password, hashed_password) - Verify password
create_session_token() - Generate unique session token
validate_session(token, expiry) - Check if session is valid
login_user(email, password) - Authenticate and create session
logout_user() - Clear session data
Add session expiration logic (24-hour timeout)
Implement secure password reset functionality
3. Login Interface
Create new login page at streamlit_app/pages/00_login.py:
Design login form with email and password fields
Add "Remember me" checkbox for 24-hour persistence
Implement form validation and error handling
Add password reset request option
Create logout button component in streamlit_app/components/logout_button.py
Style login page to match application theme
4. Session Management
Implement session state management in Streamlit:
Store authentication token in session state
Store token expiration timestamp
Store user data for authenticated users
Add cookie-based persistence for "Remember me" functionality
Implement automatic logout on session expiration
5. Authentication Middleware
Create authentication middleware in streamlit_app/utils/auth_middleware.py:
Implement require_authentication() function to protect pages
Add session validation logic
Create redirect mechanism for unauthenticated users
Update streamlit_app/app.py to use authentication middleware
Add role-based access control for admin vs. regular users
6. Secure Existing Pages
Update all page files to include authentication checks:
Add authentication requirement to 01_add_to_queue.py
Add authentication requirement to 02_view_queue.py
Add authentication requirement to all other page files
Implement role-based feature restrictions
Hide admin-only features from regular users
7. Security Enhancements
Implement rate limiting for login attempts
Add audit logging for authentication events:
Log successful/failed login attempts
Log logouts and session expirations
Log password reset requests
Ensure all authentication happens over HTTPS
Add CSRF protection for forms
8. Testing
Write unit tests for authentication functions
Create integration tests for login flow
Test session persistence across browser restarts
Test session expiration functionality
Verify role-based access restrictions
9. Documentation
Update README.md with authentication information
Document the authentication system architecture
Create user guide for login process
Document security considerations and best practices
Update API documentation if applicable
10. Deployment
Update requirements.txt with new dependencies (bcrypt, etc.)
Create database migration script if needed
Test in staging environment
Plan production rollout with minimal disruption
Monitor for authentication issues after deployment
This tasklist follows the project's style guidelines and provides a comprehensive roadmap for implementing secure user authentication in the RFQ Sender application.