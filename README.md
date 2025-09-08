# HR Recruitment & Employee Lifecycle Management System

A comprehensive HR management system built with Flask that handles the complete employee lifecycle from job requisitions to resignations, using CSV files for data persistence.

## Features

### Core Functionality
- **Job Requisitions Management**: Create, view, and close job openings
- **Candidate Management**: Add candidates individually or via bulk CSV upload
- **Recruitment Pipeline**: Structured workflow with stages (Applied → Screening → Interview → Offer → Onboarded → Resigned)
- **Document Management**: Resume upload and storage system
- **Offer Letter Generation**: Automated HTML offer letters with PDF export capability
- **Employee Onboarding**: Comprehensive checklist and progress tracking
- **Resignation Processing**: Exit checklist and final clearance tracking

### Key Features
- **CSV-Based Storage**: All data stored in local CSV files (no database required)
- **File Upload Support**: Resume and document management
- **Workflow Transitions**: Enforced business rules for stage progression
- **Admin Downloads**: Export all CSV data for external analysis
- **Responsive UI**: Bootstrap-powered interface with dark theme
- **Form Validation**: Client and server-side validation
- **Progress Tracking**: Visual progress indicators for onboarding

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML5, Bootstrap 5, Vanilla JavaScript
- **Templating**: Jinja2
- **Data Storage**: CSV files with pandas
- **File Handling**: Werkzeug secure file uploads
- **PDF Generation**: HTML-to-PDF via browser print functionality

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Installation Steps

1. **Clone or download the project files**

2. **Install required packages**:
   ```bash
   pip install flask pandas python-dotenv werkzeug
   ```

3. **Set environment variables** (optional):
   ```bash
   export SESSION_SECRET="your-secret-key-here"
   ```

4. **Run the application**:
   ```bash
   python app.py
   