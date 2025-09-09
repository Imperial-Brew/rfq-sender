"""
Box Integration Module

This module provides functions for interacting with Box, including:
- Authentication with Box
- Creating folders with hybrid structure (RFQ/part/vendor)
- Uploading files
- Creating share links

Usage:
    from box_integration import BoxIntegration

    # Initialize Box integration
    box = BoxIntegration()

    # Create a hybrid folder structure for RFQ
    folder_structure = box.create_rfq_structure(
        quote_id="QT57267",
        part_numbers=["PN-001", "PN-002"],
        vendors=["HeatTreatCo", "AnodizePro"]
    )

    # Upload files to part folders
    box.upload_part_files("PN-001", ["file1.pdf"], folder_structure["part_folders"]["PN-001"])

    # Link files to vendor folders
    box.link_files_to_vendor(
        vendor="HeatTreatCo",
        part_numbers=["PN-001"],
        part_folders=folder_structure["part_folders"],
        vendor_folder=folder_structure["vendor_folders"]["HeatTreatCo"]
    )

    # Create a share link for a vendor folder
    share_link = box.create_share_link(folder_structure["vendor_folders"]["HeatTreatCo"])
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from boxsdk import Client, OAuth2, JWTAuth
from boxsdk.exception import BoxAPIException
from boxsdk.object.collaboration import CollaborationRole
from streamlit_app.utils.box_client import get_box_client
import json


class BoxIntegration:
    """
    Box integration class for handling Box operations.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize Box integration.

        Args:
            logger: Optional logger for logging messages
        """
        self.logger = logger
        # Diagnostics fields
        self.tried_paths: list[str] = []
        self.config_path: Optional[str] = None
        self.last_error: str = ""
        self._user_identity: Optional[str] = None
        self.client = self._authenticate()

    def _authenticate(self) -> Optional[Client]:
        """
        Authenticate with Box using JWT credentials.

        New discovery order (secrets-only):
        1) st.secrets["box"]["BOX_JWT_JSON"] (Streamlit secrets)
        2) os.environ["BOX_JWT_JSON"]
        3) .streamlit/secrets.toml → [box].BOX_JWT_JSON (when running outside Streamlit)

        Returns:
            Box client if authentication is successful, None otherwise
        """
        try:
            tried: list[str] = []

            # Try Streamlit secrets first
            jwt_json = ""
            try:
                import streamlit as st
                box_secrets = getattr(st, "secrets", {}).get("box", {}) if hasattr(st, "secrets") else {}
                if isinstance(box_secrets, dict):
                    jwt_json = str(box_secrets.get("BOX_JWT_JSON", "") or "").strip()
                    if jwt_json:
                        tried.append("<st.secrets:box.BOX_JWT_JSON>")
                        self.config_path = "<secrets:box.BOX_JWT_JSON>"
            except Exception:
                # If Streamlit isn't available or secrets access fails, ignore
                pass

            # Fallback to environment variable
            if not jwt_json:
                env_jwt = os.environ.get("BOX_JWT_JSON", "").strip()
                if env_jwt:
                    jwt_json = env_jwt
                    tried.append("<env:BOX_JWT_JSON>")
                    self.config_path = "<env:BOX_JWT_JSON>"

            # Fallback to reading .streamlit/secrets.toml directly (outside Streamlit)
            if not jwt_json:
                try:
                    from core.secrets import get_section as _get_secret_section
                    box_section = _get_secret_section("box") or {}
                    file_jwt = str(box_section.get("BOX_JWT_JSON", "") or "").strip()
                    if file_jwt:
                        jwt_json = file_jwt
                        tried.append("<file:.streamlit/secrets.toml [box].BOX_JWT_JSON>")
                        self.config_path = "<file:.streamlit/secrets.toml>"
                        # Make available to downstream code in this process
                        os.environ.setdefault("BOX_JWT_JSON", jwt_json)
                except Exception:
                    pass

            # Record diagnostics
            self.tried_paths = tried

            if not jwt_json:
                msg = (
                    "Box JWT JSON not provided. Set [box].BOX_JWT_JSON in .streamlit\\secrets.toml "
                    "or export BOX_JWT_JSON as an environment variable."
                )
                self.last_error = msg
                if self.logger:
                    self.logger.error(msg)
                else:
                    print(msg)
                return None

            # Parse JWT JSON (with sanitization fallback)
            try:
                settings = json.loads(jwt_json)
            except json.JSONDecodeError:
                def _sanitize_jwt_json(text: str) -> str:
                    import re
                    def repl(m):
                        inner = m.group(1)
                        inner = inner.replace("\r\n", "\n").replace("\r", "\n")
                        inner = inner.replace("\\", "\\\\")
                        inner = inner.replace("\n", r"\n")
                        return '"privateKey": "' + inner + '"'
                    return re.sub(r'"privateKey"\s*:\s*"([\s\S]*?)"', repl, text)
                settings = json.loads(_sanitize_jwt_json(jwt_json))

            auth = JWTAuth.from_settings_dictionary(settings)
            client = Client(auth)

            # Test connection by getting current user info
            user = client.user().get()
            ident = f"{user.name} ({user.login})"
            self._user_identity = ident
            if self.logger:
                self.logger.info(f"Authenticated with Box as {ident}")
            else:
                print(f"Authenticated with Box as {ident}")

            return client

        except BoxAPIException as e:
            # Provide clearer diagnostics for common cases
            status = getattr(e, 'status', None)
            code = getattr(e, 'code', '') or ''
            message = str(e)
            self.last_error = message
            friendly = None
            if status in (401, 403) and ("unauthorized" in message.lower() or "not authorized" in message.lower() or code == "unauthorized_app"):
                friendly = (
                    "Box app is not authorized by the enterprise admin, or JWT app scopes are insufficient. "
                    "Ask your Box admin to authorize the Custom App in the Admin Console (Enterprise Settings > Apps)."
                )
            elif "invalid_grant" in message.lower() or "private_key" in message.lower() or "jwt" in message.lower():
                friendly = (
                    "JWT credential problem. Verify your BOX_JWT_JSON fields (publicKeyID, privateKey, passphrase, enterpriseID). "
                    "You may need to generate a new keypair and update the credentials."
                )
            if self.logger:
                self.logger.error(f"Box API error: {message}")
                if friendly:
                    self.logger.error(friendly)
            else:
                print(f"Box API error: {message}")
                if friendly:
                    print(friendly)
            return None

        except Exception as e:
            error_message = str(e)
            self.last_error = error_message
            if "private_key" in error_message.lower() or "jwt" in error_message.lower():
                msg = "Box JWT authentication error: Issue with JWT credentials from secrets or environment."
                if self.logger:
                    self.logger.error(msg)
                    self.logger.error(f"Original error: {error_message}")
                else:
                    print(msg)
                    print(f"Original error: {error_message}")
            else:
                if self.logger:
                    self.logger.error(f"Error authenticating with Box: {error_message}")
                else:
                    print(f"Error authenticating with Box: {error_message}")
            return None

    def diagnostics(self) -> Dict[str, Any]:
        """Return a snapshot of auth diagnostics for UI logging."""
        return {
            "tried_paths": self.tried_paths,
            "config_path": self.config_path,
            "last_error": self.last_error,
            "client_initialized": bool(self.client),
            "user": self._user_identity or "",
        }


    def create_folder(self, folder_name: str, parent_folder_id: str = "0", 
                   collaborator_email: str = "drab.dustin@athenamfg.com") -> Optional[Dict[str, Any]]:
        """
        Create a folder in Box and add a collaborator with editor access.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of the parent folder (default is "0", the root folder)
            collaborator_email: Email of the user to add as a collaborator (default is the user's email)

        Returns:
            Folder object if successful, None otherwise
        """
        if not self.client:
            if self.logger:
                self.logger.error("Box client not initialized")
            else:
                print("Box client not initialized")
            return None

        try:
            # Create folder
            folder = self.client.folder(parent_folder_id).create_subfolder(folder_name)

            if self.logger:
                self.logger.info(f"Created Box folder: {folder_name} (ID: {folder.id})")
            else:
                print(f"Created Box folder: {folder_name} (ID: {folder.id})")
                
            # Add collaborator with editor role
            try:
                if collaborator_email:
                    # Create a collaboration directly using the Box API
                    url = f"https://api.box.com/2.0/collaborations"
                    headers = {
                        "Authorization": f"Bearer {self.client.auth.access_token}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "item": {
                            "id": folder.id,
                            "type": "folder"
                        },
                        "accessible_by": {
                            "login": collaborator_email,
                            "type": "user"
                        },
                        "role": "editor"
                    }
                    
                    import requests
                    response = requests.post(url, headers=headers, json=data)
                    
                    if response.status_code in (200, 201):
                        collaboration = response.json()
                    else:
                        raise Exception(f"Failed to add collaborator: {response.text}")
                    
                    if self.logger:
                        self.logger.info(f"Added {collaborator_email} as collaborator to folder {folder_name}")
                    else:
                        print(f"Added {collaborator_email} as collaborator to folder {folder_name}")
            except Exception as collab_error:
                if self.logger:
                    self.logger.warning(f"Failed to add collaborator to folder: {str(collab_error)}")
                else:
                    print(f"Failed to add collaborator to folder: {str(collab_error)}")
                # Continue even if adding collaborator fails - we still want to return the folder

            return folder

        except BoxAPIException as e:
            # Check if the error is because the folder already exists
            if "item_name_in_use" in str(e):
                # Try to get the existing folder
                items = self.client.folder(parent_folder_id).get_items()
                for item in items:
                    if item.name == folder_name and item.type == "folder":
                        if self.logger:
                            self.logger.info(f"Using existing Box folder: {folder_name} (ID: {item.id})")
                        else:
                            print(f"Using existing Box folder: {folder_name} (ID: {item.id})")
                        
                        # Add collaborator to existing folder
                        try:
                            if collaborator_email:
                                # Create a collaboration directly using the Box API
                                url = f"https://api.box.com/2.0/collaborations"
                                headers = {
                                    "Authorization": f"Bearer {self.client.auth.access_token}",
                                    "Content-Type": "application/json"
                                }
                                data = {
                                    "item": {
                                        "id": item.id,
                                        "type": "folder"
                                    },
                                    "accessible_by": {
                                        "login": collaborator_email,
                                        "type": "user"
                                    },
                                    "role": "editor"
                                }
                                
                                import requests
                                response = requests.post(url, headers=headers, json=data)
                                
                                if response.status_code in (200, 201):
                                    collaboration = response.json()
                                else:
                                    raise Exception(f"Failed to add collaborator: {response.text}")
                                
                                if self.logger:
                                    self.logger.info(f"Added {collaborator_email} as collaborator to existing folder {folder_name}")
                                else:
                                    print(f"Added {collaborator_email} as collaborator to existing folder {folder_name}")
                        except Exception as collab_error:
                            if self.logger:
                                self.logger.warning(f"Failed to add collaborator to existing folder: {str(collab_error)}")
                            else:
                                print(f"Failed to add collaborator to existing folder: {str(collab_error)}")
                            # Continue even if adding collaborator fails
                            
                        return item

            if self.logger:
                self.logger.error(f"Box API error creating folder: {str(e)}")
            else:
                print(f"Box API error creating folder: {str(e)}")
            return None

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating Box folder: {str(e)}")
            else:
                print(f"Error creating Box folder: {str(e)}")
            return None

    def upload_file(self, file_path: str, folder: Dict[str, Any], 
                  timeout: int = 300, max_retries: int = 3, 
                  chunk_size: int = 8 * 1024 * 1024) -> Optional[Dict[str, Any]]:
        """
        Upload a file to a Box folder with retry logic and progress reporting.

        Args:
            file_path: Path to the file to upload
            folder: Box folder object
            timeout: Timeout in seconds for the upload operation (default: 300s/5min)
            max_retries: Maximum number of retry attempts for failed uploads (default: 3)
            chunk_size: Size of chunks for large file uploads in bytes (default: 8MB)

        Returns:
            File object if successful, None otherwise
        """
        if not self.client:
            if self.logger:
                self.logger.error("Box client not initialized")
            else:
                print("Box client not initialized")
            return None

        if not os.path.exists(file_path):
            if self.logger:
                self.logger.error(f"File not found: {file_path}")
            else:
                print(f"File not found: {file_path}")
            return None

        # Get file name and size
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Log the upload attempt
        if self.logger:
            self.logger.info(f"Uploading file to Box: {file_name} ({file_size_mb:.2f} MB)")
        else:
            print(f"Uploading file to Box: {file_name} ({file_size_mb:.2f} MB)")
        
        # Determine if we should use chunked upload for large files
        use_chunked_upload = file_size > chunk_size
        
        # Initialize retry counter
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # If this is a retry, log it
                if retry_count > 0:
                    if self.logger:
                        self.logger.info(f"Retry attempt {retry_count}/{max_retries} for file: {file_name}")
                    else:
                        print(f"Retry attempt {retry_count}/{max_retries} for file: {file_name}")
                
                # For large files, use chunked upload with progress reporting
                if use_chunked_upload:
                    # Calculate number of chunks
                    total_chunks = (file_size + chunk_size - 1) // chunk_size
                    
                    if self.logger:
                        self.logger.info(f"Using chunked upload for {file_name} ({total_chunks} chunks)")
                    else:
                        print(f"Using chunked upload for {file_name} ({total_chunks} chunks)")
                    
                    # Create upload session
                    upload_session = self.client.folder(folder.id).create_upload_session(
                        file_size=file_size,
                        file_name=file_name
                    )
                    
                    # Upload chunks
                    with open(file_path, 'rb') as file_content:
                        for chunk_index in range(total_chunks):
                            # Calculate chunk position
                            start_byte = chunk_index * chunk_size
                            end_byte = min(start_byte + chunk_size, file_size)
                            chunk_length = end_byte - start_byte
                            
                            # Read chunk
                            file_content.seek(start_byte)
                            chunk_data = file_content.read(chunk_length)
                            
                            # Upload chunk with timeout
                            upload_session.upload_part_bytes(
                                chunk_data,
                                start_byte,
                                end_byte - 1,
                                file_size
                            )
                            
                            # Log progress
                            progress_percent = (chunk_index + 1) / total_chunks * 100
                            if self.logger:
                                self.logger.debug(f"Uploaded chunk {chunk_index + 1}/{total_chunks} ({progress_percent:.1f}%) for {file_name}")
                            else:
                                print(f"Uploaded chunk {chunk_index + 1}/{total_chunks} ({progress_percent:.1f}%) for {file_name}")
                    
                    # Commit the upload session
                    uploaded_file = upload_session.commit()
                else:
                    # For smaller files, use regular upload
                    with open(file_path, 'rb') as file_content:
                        uploaded_file = self.client.folder(folder.id).upload_stream(
                            file_content,
                            file_name
                        )
                
                # Log success
                if self.logger:
                    self.logger.info(f"Successfully uploaded file to Box: {file_name} (ID: {uploaded_file.id})")
                else:
                    print(f"Successfully uploaded file to Box: {file_name} (ID: {uploaded_file.id})")
                
                return uploaded_file
                
            except BoxAPIException as e:
                # Check if the error is because the file already exists
                if "item_name_in_use" in str(e):
                    # Try to get the existing file
                    items = self.client.folder(folder.id).get_items()
                    for item in items:
                        if item.name == file_name and item.type == "file":
                            if self.logger:
                                self.logger.info(f"File already exists in Box: {file_name} (ID: {item.id})")
                            else:
                                print(f"File already exists in Box: {file_name} (ID: {item.id})")
                            return item
                
                # For other API errors, check if we should retry
                retry_count += 1
                
                if retry_count <= max_retries:
                    # Log retry attempt
                    if self.logger:
                        self.logger.warning(f"Box API error uploading file (will retry): {str(e)}")
                    else:
                        print(f"Box API error uploading file (will retry): {str(e)}")
                    
                    # Wait before retrying (exponential backoff)
                    import time
                    wait_time = 2 ** retry_count  # 2, 4, 8 seconds
                    time.sleep(wait_time)
                else:
                    # Log final failure
                    if self.logger:
                        self.logger.error(f"Box API error uploading file (max retries exceeded): {str(e)}")
                    else:
                        print(f"Box API error uploading file (max retries exceeded): {str(e)}")
                    return None
                    
            except Exception as e:
                # For general exceptions, check if we should retry
                retry_count += 1
                
                if retry_count <= max_retries:
                    # Log retry attempt
                    if self.logger:
                        self.logger.warning(f"Error uploading file to Box (will retry): {str(e)}")
                    else:
                        print(f"Error uploading file to Box (will retry): {str(e)}")
                    
                    # Wait before retrying (exponential backoff)
                    import time
                    wait_time = 2 ** retry_count  # 2, 4, 8 seconds
                    time.sleep(wait_time)
                else:
                    # Log final failure
                    if self.logger:
                        self.logger.error(f"Error uploading file to Box (max retries exceeded): {str(e)}")
                    else:
                        print(f"Error uploading file to Box (max retries exceeded): {str(e)}")
                    return None
        
        # This should not be reached, but just in case
        return None

    def upload_files(self, file_paths: List[str], folder: Dict[str, Any], 
                   timeout: int = 300, max_retries: int = 3, 
                   chunk_size: int = 8 * 1024 * 1024) -> List[Dict[str, Any]]:
        """
        Upload multiple files to a Box folder.

        Args:
            file_paths: List of paths to files to upload
            folder: Box folder object
            timeout: Timeout in seconds for each upload operation (default: 300s/5min)
            max_retries: Maximum number of retry attempts for failed uploads (default: 3)
            chunk_size: Size of chunks for large file uploads in bytes (default: 8MB)

        Returns:
            List of uploaded file objects
        """
        uploaded_files = []
        total_files = len(file_paths)

        if self.logger:
            self.logger.info(f"Uploading {total_files} files to Box folder {folder.name} (ID: {folder.id})")
        else:
            print(f"Uploading {total_files} files to Box folder {folder.name} (ID: {folder.id})")

        for index, file_path in enumerate(file_paths, 1):
            if self.logger:
                self.logger.info(f"Processing file {index}/{total_files}: {os.path.basename(file_path)}")
            else:
                print(f"Processing file {index}/{total_files}: {os.path.basename(file_path)}")
                
            uploaded_file = self.upload_file(
                file_path, 
                folder, 
                timeout=timeout, 
                max_retries=max_retries, 
                chunk_size=chunk_size
            )
            
            if uploaded_file:
                uploaded_files.append(uploaded_file)

        if self.logger:
            self.logger.info(f"Completed uploading {len(uploaded_files)}/{total_files} files to Box folder {folder.name}")
        else:
            print(f"Completed uploading {len(uploaded_files)}/{total_files} files to Box folder {folder.name}")

        return uploaded_files

    def create_share_link(self, folder: Dict[str, Any], access: str = "open", password: str = None, expire_days: int = None) -> Optional[str]:
        """
        Create a share link for a Box folder.

        Args:
            folder: Box folder object
            access: Access level for the shared link (open, company, collaborators)
            password: Optional password protection for the shared link
            expire_days: Optional number of days until the link expires

        Returns:
            Share link URL if successful, None otherwise
        """
        if not self.client:
            if self.logger:
                self.logger.error("Box client not initialized")
            else:
                print("Box client not initialized")
            return None

        try:
            # Create shared link with enhanced options
            updated_folder = self.client.folder(folder.id).get()
            
            # Set up shared link parameters
            shared_link_params = {
                'access': access,
                'allow_download': True,
                'allow_preview': True,
            }
            
            # Add password if provided
            if password:
                shared_link_params['password'] = password
                
            # Add expiration if provided
            if expire_days and expire_days > 0:
                from datetime import datetime, timedelta
                expire_date = datetime.now() + timedelta(days=expire_days)
                shared_link_params['unshared_at'] = expire_date.isoformat()
            
            # Create the shared link
            shared_link = updated_folder.get_shared_link(**shared_link_params)

            if self.logger:
                log_message = f"Created Box share link for folder: {folder.name}"
                if password:
                    log_message += " (password protected)"
                if expire_days:
                    log_message += f" (expires in {expire_days} days)"
                self.logger.info(log_message)
                self.logger.info(f"Share link: {shared_link}")
            else:
                log_message = f"Created Box share link for folder: {folder.name}"
                if password:
                    log_message += " (password protected)"
                if expire_days:
                    log_message += f" (expires in {expire_days} days)"
                print(log_message)
                print(f"Share link: {shared_link}")

            return shared_link

        except BoxAPIException as e:
            if self.logger:
                self.logger.error(f"Box API error creating share link: {str(e)}")
            else:
                print(f"Box API error creating share link: {str(e)}")
            return None

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating Box share link: {str(e)}")
            else:
                print(f"Error creating Box share link: {str(e)}")
            return None
            
    def create_rfq_structure(self, quote_id: str, part_numbers: List[str], vendors: List[str]) -> Dict[str, Any]:
        """
        Create the hybrid folder structure for an RFQ as described in box_structure.md.
        
        Args:
            quote_id: The quote or order number (e.g., QT57267)
            part_numbers: List of part numbers to create folders for
            vendors: List of vendor names to create folders for
            
        Returns:
            Dictionary containing folder objects and IDs
        """
        if not self.client:
            if self.logger:
                self.logger.error("Box client not initialized")
            else:
                print("Box client not initialized")
            return None
            
        try:
            # Create master RFQ folder
            if self.logger:
                self.logger.info(f"Creating master RFQ folder: {quote_id}")
            else:
                print(f"Creating master RFQ folder: {quote_id}")
                
            master_folder = self.create_folder(quote_id)
            
            if not master_folder:
                if self.logger:
                    self.logger.error(f"Failed to create master RFQ folder: {quote_id}")
                else:
                    print(f"Failed to create master RFQ folder: {quote_id}")
                return None
            
            # Create part folders
            part_folders = {}
            for part_number in part_numbers:
                if self.logger:
                    self.logger.info(f"Creating part folder: {part_number}")
                else:
                    print(f"Creating part folder: {part_number}")
                    
                part_folder = self.create_folder(part_number, parent_folder_id=master_folder.id)
                
                if part_folder:
                    part_folders[part_number] = part_folder
                else:
                    if self.logger:
                        self.logger.warning(f"Failed to create part folder: {part_number}")
                    else:
                        print(f"Failed to create part folder: {part_number}")
            
            # Create vendor_links folder
            if self.logger:
                self.logger.info("Creating vendor_links folder")
            else:
                print("Creating vendor_links folder")
                
            vendor_links_folder = self.create_folder("vendor_links", parent_folder_id=master_folder.id)
            
            if not vendor_links_folder:
                if self.logger:
                    self.logger.error("Failed to create vendor_links folder")
                else:
                    print("Failed to create vendor_links folder")
                return {
                    "master_folder": master_folder,
                    "part_folders": part_folders,
                    "vendor_links_folder": None,
                    "vendor_folders": {}
                }
            
            # Create vendor folders
            vendor_folders = {}
            for vendor in vendors:
                if self.logger:
                    self.logger.info(f"Creating vendor folder: {vendor}")
                else:
                    print(f"Creating vendor folder: {vendor}")
                    
                vendor_folder = self.create_folder(vendor, parent_folder_id=vendor_links_folder.id)
                
                if vendor_folder:
                    vendor_folders[vendor] = vendor_folder
                else:
                    if self.logger:
                        self.logger.warning(f"Failed to create vendor folder: {vendor}")
                    else:
                        print(f"Failed to create vendor folder: {vendor}")
            
            return {
                "master_folder": master_folder,
                "part_folders": part_folders,
                "vendor_links_folder": vendor_links_folder,
                "vendor_folders": vendor_folders
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating RFQ folder structure: {str(e)}")
            else:
                print(f"Error creating RFQ folder structure: {str(e)}")
            return None
            
    def upload_part_files(self, part_number: str, files: List[str], part_folder: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Upload files for a specific part to its folder.
        
        Args:
            part_number: The part number
            files: List of file paths for this part
            part_folder: The part folder object
            
        Returns:
            List of uploaded file objects
        """
        if not self.client or not part_folder:
            if self.logger:
                self.logger.error("Box client not initialized or part folder is None")
            else:
                print("Box client not initialized or part folder is None")
            return []
            
        try:
            if self.logger:
                self.logger.info(f"Uploading {len(files)} files to part folder: {part_number}")
            else:
                print(f"Uploading {len(files)} files to part folder: {part_number}")
                
            return self.upload_files(files, part_folder)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error uploading files to part folder: {str(e)}")
            else:
                print(f"Error uploading files to part folder: {str(e)}")
            return []
            
    def link_files_to_vendor(self, vendor: str, part_numbers: List[str], 
                           part_folders: Dict[str, Dict[str, Any]], 
                           vendor_folder: Dict[str, Any]) -> bool:
        """
        Create links to part files in vendor folder.
        
        Args:
            vendor: Vendor name
            part_numbers: List of part numbers this vendor is quoting
            part_folders: Dictionary of part folders
            vendor_folder: The vendor folder object
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not vendor_folder:
            if self.logger:
                self.logger.error("Box client not initialized or vendor folder is None")
            else:
                print("Box client not initialized or vendor folder is None")
            return False
            
        try:
            success_count = 0
            
            for part_number in part_numbers:
                part_folder = part_folders.get(part_number)
                if not part_folder:
                    if self.logger:
                        self.logger.warning(f"Part folder not found for part number: {part_number}")
                    else:
                        print(f"Part folder not found for part number: {part_number}")
                    continue
                    
                # Get files from part folder
                items = self.client.folder(part_folder.id).get_items()
                
                for item in items:
                    if item.type == "file":
                        try:
                            # Create a shortcut/link in the vendor folder
                            if self.logger:
                                self.logger.info(f"Creating link for file {item.name} in vendor folder: {vendor}")
                            else:
                                print(f"Creating link for file {item.name} in vendor folder: {vendor}")
                                
                            # Use the Box API to create a web link
                            web_link = self.client.folder(vendor_folder.id).create_web_link(
                                name=f"{part_number}_{item.name}",
                                url=f"https://app.box.com/file/{item.id}"
                            )
                            
                            success_count += 1
                            
                        except Exception as link_error:
                            if self.logger:
                                self.logger.warning(f"Failed to create link for file {item.name}: {str(link_error)}")
                            else:
                                print(f"Failed to create link for file {item.name}: {str(link_error)}")
            
            if self.logger:
                self.logger.info(f"Created {success_count} links in vendor folder: {vendor}")
            else:
                print(f"Created {success_count} links in vendor folder: {vendor}")
                
            return success_count > 0
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error linking files to vendor folder: {str(e)}")
            else:
                print(f"Error linking files to vendor folder: {str(e)}")
            return False