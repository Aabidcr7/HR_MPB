# Overview

An HR Recruitment & Employee Lifecycle Management System built with Flask that handles the complete employee journey from job requisitions to resignations. The system uses CSV files as the primary data storage mechanism, making it lightweight and database-independent. It provides a comprehensive workflow for managing job postings, candidate applications, screening processes, interviews, offer generation, employee onboarding, and resignation handling.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework Architecture
- **Flask-based MVC pattern**: Single-file Flask application (`app.py`) serving as the main controller with route handlers for all CRUD operations
- **Jinja2 templating**: Server-side rendering with template inheritance using a base template for consistent UI structure
- **Static asset organization**: Separate CSS and JavaScript files for styling and client-side functionality

## Data Storage Strategy
- **CSV-first approach**: All persistent data stored in local CSV files instead of traditional databases
- **Pandas integration**: Uses pandas DataFrames for CSV manipulation, providing robust data handling capabilities
- **File-based workflow**: Seven core CSV files (requisitions, candidates, screening, interviews, offers, onboarding, resignations) represent different stages of the employee lifecycle
- **Auto-incrementing IDs**: Custom utility functions generate sequential IDs for each CSV table

## Business Logic & Workflow
- **Stage-based progression**: Candidates move through defined stages (Applied → Screening → Interview → Offer → Onboarded → Resigned) with enforced business rules
- **Conditional transitions**: Only "Shortlisted" candidates advance to next stages; rejected/hold candidates remain at current stage
- **Document management**: File upload system for resumes and onboarding documents with secure filename handling

## Frontend Architecture
- **Bootstrap 5 dark theme**: Responsive UI framework with consistent styling across all pages
- **Progressive enhancement**: Minimal JavaScript for form validation, file uploads, and UI interactions
- **Modal-based forms**: Pop-up forms for quick actions like creating requisitions and adding candidates
- **Client-side validation**: File type and size validation before form submission

## File Management System
- **Secure uploads**: Werkzeug-based file handling with filename sanitization and type validation
- **Organized storage**: Separate directories for uploads (resumes/documents) and CSV templates
- **Resume streaming**: Direct file serving for resume downloads with proper content types

## Offer Letter Generation
- **HTML-to-PDF workflow**: Generates professional offer letters as HTML templates with print-to-PDF functionality
- **Template-based system**: Standardized offer letter format with dynamic candidate and company information
- **Browser-native PDF export**: Leverages browser printing capabilities instead of external PDF libraries

# External Dependencies

## Python Packages
- **Flask**: Core web framework for routing, templating, and request handling
- **Pandas**: Data manipulation library for CSV operations and DataFrame management
- **Werkzeug**: WSGI utilities for secure file uploads and filename handling
- **python-dotenv**: Environment variable management for configuration

## Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design and dark theme support
- **Font Awesome 6**: Icon library for consistent UI iconography
- **Vanilla JavaScript**: No external JS frameworks; uses native DOM manipulation and Bootstrap components

## File System Dependencies
- **Local storage**: Relies on filesystem access for CSV files and uploaded documents
- **Directory structure**: Creates and manages `uploads/` and `csv_templates/` directories
- **No database**: Completely database-independent architecture using only file-based storage

## Browser Capabilities
- **PDF generation**: Depends on browser's native print-to-PDF functionality for offer letter export
- **File uploads**: Uses HTML5 file input capabilities with JavaScript validation
- **Modern browser features**: Requires JavaScript-enabled browser for optimal functionality