# RFQ Sender System

A modern system for managing and sending Request for Quote (RFQ) emails to multiple vendors for finishing, material, and hardware quotes. Featuring a React frontend and FastAPI backend.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Development](#development)
- [Scalability](#scalability)
- [Contributing](#contributing)
- [License](#license)

## Problem Statement

- Need to manage quotes for finishing/material/hardware
- Working with multiple vendors, each with multiple contacts
- Dealing with various processes with different industry names and specifications
- Managing customers with their own internal naming conventions
- Handling file sharing with security requirements (CUI/ITAR)

## Solution

The RFQ Sender System provides:

- **React Web Interface**: Modern, responsive UI for queue and vendor management.
- **FastAPI Backend**: High-performance API for data processing and integration.
- **Secure File Sharing**: CUI/ITAR compliant sharing via Box integration.
- **Accurate Specifications**: Process specifications mapping to vendor-friendly data.
- **Automated Drafting**: Integration with Microsoft Graph for automated Outlook drafts.
- **BOM Integration**: File preparation and organization based on Bill of Materials.

## Project Structure

```
rfq-sender/
├── api/              # FastAPI backend application
├── cli/              # Command-line interface tools
├── config/           # Configuration files (vendors, email settings)
├── core/             # Core application modules
├── data_raw/         # Raw data files (CSV, input files)
├── data_cleaned/     # Processed data files (databases, cleaned data)
├── docs/             # Documentation
├── frontend/         # React (Vite + TypeScript) web application
├── logs/             # Application logs
├── scripts/          # Python scripts
├── templates/        # Jinja2 templates for emails and forms
├── tests/            # Test files
└── utils/            # Utility modules (specs, queue, email, auth)
```

## Setup

### Backend (Python)

1. Clone this repository
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-api.txt
   ```
4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Edit `.env` with your actual configuration values

### Frontend (React)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## Usage

### Running the API

Start the FastAPI server:
```bash
uvicorn api.main:app --reload
```
The API documentation will be available at `http://localhost:8000/docs`.

### Running the CLI

CLI tools are available in the `cli/` directory for automation.

### Mail backend (Microsoft Graph)

The system uses Microsoft Graph to create Draft emails.

- Configure your Azure app credentials and company information in your environment variables or `.env` file.
- Use `scripts/smoke_graph.py` to verify Graph connectivity.

## Environment Variables

The application uses environment variables for configuration. See `.env.example` for a full list.

### Box Integration

Box integration uses JWT authentication. 
1. Create a Box Custom App with JWT.
2. Save the configuration JSON as `scripts/box/0__config.json`.
3. For more details on the hybrid folder structure, see [Box Hybrid Structure](.junie/mds/box_hybrid_structure.md).

## Development

This project follows the style guidelines in [.junie/mds/guidelines.md](.junie/mds/guidelines.md).

### Testing
Run tests using pytest:
```bash
pytest
```

## Scalability

The RFQ Sender system is designed to handle a moderate volume of RFQs. For larger scale operations:
- **Database**: Migrate from SQLite to PostgreSQL.
- **Async**: API is built on FastAPI for asynchronous performance.
- **Storage**: Leverages Box for scalable, secure file storage.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
