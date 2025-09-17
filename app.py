import os
import csv
import pandas as pd
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response, Response
import uuid
import io

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "hr-system-secret-key")

# Configuration
UPLOAD_FOLDER = 'uploads'
CSV_FOLDER = 'csv_templates'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'csv'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CSV_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_next_id(csv_file_path):
    """Get the next available ID for a CSV file"""
    try:
        if os.path.exists(csv_file_path):
            df = pd.read_csv(csv_file_path)
            if not df.empty and 'id' in df.columns:
                return df['id'].max() + 1
        return 1
    except Exception as e:
        logging.error(f"Error getting next ID: {e}")
        return 1

def read_csv_safe(csv_file_path):
    """Safely read CSV file"""
    try:
        if os.path.exists(csv_file_path):
            return pd.read_csv(csv_file_path)
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error reading CSV {csv_file_path}: {e}")
        return pd.DataFrame()

def write_csv_safe(df, csv_file_path):
    """Safely write CSV file"""
    try:
        df.to_csv(csv_file_path, index=False)
        return True
    except Exception as e:
        logging.error(f"Error writing CSV {csv_file_path}: {e}")
        return False

def append_to_csv(data, csv_file_path):
    """Append data to CSV file"""
    try:
        df = read_csv_safe(csv_file_path)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        return write_csv_safe(df, csv_file_path)
    except Exception as e:
        logging.error(f"Error appending to CSV {csv_file_path}: {e}")
        return False

def update_candidate_stage(candidate_id, new_stage):
    """Update candidate's stage in candidates.csv"""
    csv_path = os.path.join(CSV_FOLDER, 'candidates.csv')
    df = read_csv_safe(csv_path)
    if not df.empty:
        df.loc[df['id'] == int(candidate_id), 'stage'] = new_stage
        return write_csv_safe(df, csv_path)
    return False

@app.route('/')
def dashboard():
    """Main dashboard showing requisitions and quick statistics"""
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    interviews_df = read_csv_safe(os.path.join(CSV_FOLDER, 'interviews.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))

    # Compute quick stats
    try:
        open_requisitions = int((requisitions_df['status'] == 'Open').sum()) if not requisitions_df.empty else 0
    except Exception:
        open_requisitions = 0

    try:
        active_candidates = int((candidates_df['stage'].isin(['Applied', 'Screening', 'Screening Hold', 'Interview', 'Interview Hold'])).sum()) if not candidates_df.empty else 0
    except Exception:
        active_candidates = 0

    try:
        interviews_pending = int((candidates_df['stage'].isin(['Screening', 'Interview'])).sum()) if not candidates_df.empty else 0
    except Exception:
        interviews_pending = 0

    try:
        offers_extended = int(len(offers_df)) if not offers_df.empty else 0
    except Exception:
        offers_extended = 0

    stats = {
        'open_requisitions': open_requisitions,
        'active_candidates': active_candidates,
        'interviews_pending': interviews_pending,
        'offers_extended': offers_extended,
    }

    return render_template('dashboard.html', requisitions=requisitions_df.to_dict('records'), stats=stats)

@app.route('/requisitions', methods=['GET', 'POST'])
def requisitions():
    if request.method == 'POST':
        # Create new requisition
        requisition_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'requisitions.csv')),
            'start_date': request.form['start_date'],
            'end_date': request.form['end_date'],
            'manager_name': request.form['manager_name'],
            'position_title': request.form['position_title'],
            'job_description': request.form['job_description'],
            'number_of_openings': request.form['number_of_openings'],
            'department': request.form['department'],
            'location': request.form['location'],
            'salary_min': request.form['salary_min'],
            'salary_max': request.form['salary_max'],
            'job_type': request.form['job_type'],
            'requirements': request.form['requirements'],
            'status': 'Open',
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if append_to_csv(requisition_data, os.path.join(CSV_FOLDER, 'requisitions.csv')):
            flash('Requisition created successfully!', 'success')
        else:
            flash('Error creating requisition!', 'error')
        
        return redirect(url_for('dashboard'))
    
    return redirect(url_for('dashboard'))

@app.route('/requisitions/<int:req_id>/close', methods=['POST'])
def close_requisition(req_id):
    """Close a job requisition"""
    csv_path = os.path.join(CSV_FOLDER, 'requisitions.csv')
    df = read_csv_safe(csv_path)
    if not df.empty:
        df.loc[df['id'] == req_id, 'status'] = 'Closed'
        if write_csv_safe(df, csv_path):
            flash('Requisition closed successfully!', 'success')
        else:
            flash('Error closing requisition!', 'error')
    return redirect(url_for('dashboard'))

@app.route('/requisitions/<int:req_id>')
def requisition_detail(req_id):
    """Show requisition details with candidates"""
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    
    requisition = requisitions_df[requisitions_df['id'] == req_id].to_dict('records')
    if not requisition:
        flash('Requisition not found!', 'error')
        return redirect(url_for('dashboard'))
    
    requisition = requisition[0]
    req_candidates = candidates_df[candidates_df['requisition_id'] == req_id].to_dict('records')
    
    return render_template('requisition_detail.html', requisition=requisition, candidates=req_candidates)

@app.route('/requisitions/<int:req_id>/candidates', methods=['POST'])
def add_candidate(req_id):
    """Add a single candidate to a requisition"""
    try:
        # Handle resume upload
        resume_filename = None
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add unique identifier to filename
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                resume_filename = unique_filename
        
        candidate_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'candidates.csv')),
            'requisition_id': req_id,
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'experience': request.form['experience'],
            'skills': request.form['skills'],
            'resume_filename': resume_filename or '',
            'stage': 'Applied',
            'applied_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_salary': request.form.get('current_salary', ''),
            'expected_salary': request.form.get('expected_salary', ''),
            'notice_period': request.form.get('notice_period', ''),
            'source': request.form.get('source', '')
        }
        
        if append_to_csv(candidate_data, os.path.join(CSV_FOLDER, 'candidates.csv')):
            flash('Candidate added successfully!', 'success')
        else:
            flash('Error adding candidate!', 'error')
            
    except Exception as e:
        logging.error(f"Error adding candidate: {e}")
        flash('Error adding candidate!', 'error')
    
    return redirect(url_for('requisition_detail', req_id=req_id))

@app.route('/candidates/bulk-sample')
def download_bulk_candidate_sample():
    """Provide a sample CSV for candidates bulk upload"""
    sample_headers = [
        'requisition_id', 'name', 'email', 'phone', 'experience', 'skills',
        'current_salary', 'expected_salary', 'notice_period', 'source', 'resume_filename'
    ]
    sample_rows = [
        ['1', 'John Doe', 'john@example.com', '9999999999', '5', 'Python, Flask', '₹800000', '₹1000000', '30', 'Job Board', 'john_doe_resume.pdf'],
        ['2', 'Jane Smith', 'jane@example.com', '8888888888', '3', 'SQL, Excel', '₹600000', '₹750000', '15', 'Referral', 'jane_smith_resume.pdf'],
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(sample_headers)
    writer.writerows(sample_rows)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=candidates_bulk_sample.csv'
        }
    )

@app.route('/candidates/bulk-upload', methods=['POST'])
def bulk_upload_candidates():
    """Handle CSV + resume files upload to bulk-add candidates"""
    # Expect a single multi-file input named 'bulk_files' containing one CSV and multiple resume files
    uploaded_files = request.files.getlist('bulk_files') if 'bulk_files' in request.files else []
    if not uploaded_files:
        flash('Please select a CSV file (and resume files).', 'error')
        return redirect(request.referrer)

    csv_file = None
    resume_files = []
    for f in uploaded_files:
        if not f or not f.filename:
            continue
        if f.filename.lower().endswith('.csv') and csv_file is None:
            csv_file = f
        else:
            resume_files.append(f)

    if not csv_file:
        flash('No CSV file found in selection.', 'error')
        return redirect(request.referrer)

    try:
        # Save resumes and map original names to unique saved names
        original_to_saved_resume = {}
        for resume_file in resume_files:
            if not allowed_file(resume_file.filename):
                continue
            original_name = secure_filename(resume_file.filename)
            unique_name = f"{uuid.uuid4()}_{original_name}"
            resume_file.save(os.path.join(UPLOAD_FOLDER, unique_name))
            original_to_saved_resume[original_name] = unique_name

        # Read uploaded CSV
        stream = io.StringIO(csv_file.stream.read().decode('UTF8'), newline=None)
        csv_input = csv.DictReader(stream)

        candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))

        count = 0
        for row in csv_input:
            # Basic normalization
            row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

            # Map optional resume filename to saved file if provided
            saved_resume = ''
            if 'resume_filename' in row and row['resume_filename']:
                original_name = secure_filename(row['resume_filename'])
                saved_resume = original_to_saved_resume.get(original_name, '')

            candidate_data = {
                'id': get_next_id(os.path.join(CSV_FOLDER, 'candidates.csv')),
                'requisition_id': int(row.get('requisition_id', 0) or 0),
                'name': row.get('name', ''),
                'email': row.get('email', ''),
                'phone': row.get('phone', ''),
                'experience': row.get('experience', ''),
                'skills': row.get('skills', ''),
                'current_salary': row.get('current_salary', ''),
                'expected_salary': row.get('expected_salary', ''),
                'notice_period': row.get('notice_period', ''),
                'source': row.get('source', ''),
                'applied_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stage': 'Applied',
                'resume_filename': saved_resume,
            }

            candidates_df = pd.concat([candidates_df, pd.DataFrame([candidate_data])], ignore_index=True)
            count += 1

        if write_csv_safe(candidates_df, os.path.join(CSV_FOLDER, 'candidates.csv')):
            flash(f'Successfully uploaded {count} candidates.', 'success')
        else:
            flash('Error saving candidates!', 'error')

    except Exception as e:
        logging.error(f"Error in bulk upload: {e}")
        flash('Error processing bulk upload!', 'error')

    return redirect(request.referrer)

@app.route('/candidates/<int:cand_id>/resume')
def get_resume(cand_id):
    """Stream the resume file"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    resume_filename = candidate.iloc[0]['resume_filename']
    if not resume_filename:
        flash('No resume found for this candidate!', 'error')
        return redirect(request.referrer)
    
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, resume_filename), as_attachment=True)
    except FileNotFoundError:
        flash('Resume file not found!', 'error')
        return redirect(request.referrer)

@app.route('/candidates/<int:cand_id>/resume-preview')
def preview_resume(cand_id):
    """Preview the resume file inline"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        return "Candidate not found", 404
    
    resume_filename = candidate.iloc[0]['resume_filename']
    if not resume_filename:
        return "No resume found for this candidate", 404
    
    try:
        file_path = os.path.join(UPLOAD_FOLDER, resume_filename)
        if not os.path.exists(file_path):
            return "Resume file not found", 404
        
        # Get file extension to determine content type
        file_ext = resume_filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain'
        }
        
        content_type = content_types.get(file_ext, 'application/octet-stream')
        
        return send_file(file_path, mimetype=content_type, as_attachment=False)
    except Exception as e:
        logging.error(f"Error previewing resume: {e}")
        return "Error loading resume", 500

@app.route('/screening/<int:cand_id>')
def screening_form(cand_id):
    """Show screening form for a candidate"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('screening_form.html', candidate=candidate.iloc[0].to_dict())

@app.route('/screening', methods=['POST'])
def submit_screening():
    """Submit screening result"""
    try:
        candidate_id = int(request.form['candidate_id'])
        
        screening_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'screening.csv')),
            'candidate_id': candidate_id,
            'screener_name': request.form['screener_name'],
            'technical_score': request.form['technical_score'],
            'communication_score': request.form['communication_score'],
            'experience_score': request.form['experience_score'],
            'overall_score': request.form['overall_score'],
            'comments': request.form['comments'],
            'status': request.form['status'],
            'screening_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if append_to_csv(screening_data, os.path.join(CSV_FOLDER, 'screening.csv')):
            # Update candidate stage based on screening status
            status_value = request.form['status']
            if status_value == 'Shortlisted':
                update_candidate_stage(candidate_id, 'Screening')
            elif status_value == 'Rejected':
                update_candidate_stage(candidate_id, 'Rejected')
            elif status_value == 'Hold':
                update_candidate_stage(candidate_id, 'Screening Hold')
            flash('Screening result submitted successfully!', 'success')
        else:
            flash('Error submitting screening result!', 'error')
            
    except Exception as e:
        logging.error(f"Error submitting screening: {e}")
        flash('Error submitting screening result!', 'error')
    
    return redirect(request.referrer)

@app.route('/interview/<int:cand_id>')
def interview_form(cand_id):
    """Show interview form for a candidate"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('interview_form.html', candidate=candidate.iloc[0].to_dict())

@app.route('/interview', methods=['POST'])
def submit_interview():
    """Submit interview result"""
    try:
        candidate_id = int(request.form['candidate_id'])
        
        interview_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'interviews.csv')),
            'candidate_id': candidate_id,
            'interviewer_name': request.form['interviewer_name'],
            'interview_type': request.form['interview_type'],
            'technical_score': request.form['technical_score'],
            'problem_solving_score': request.form['problem_solving_score'],
            'communication_score': request.form['communication_score'],
            'cultural_fit_score': request.form['cultural_fit_score'],
            'overall_score': request.form['overall_score'],
            'comments': request.form['comments'],
            'status': request.form['status'],
            'interview_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if append_to_csv(interview_data, os.path.join(CSV_FOLDER, 'interviews.csv')):
            # Update candidate stage based on interview status
            status_value = request.form['status']
            if status_value == 'Shortlisted':
                update_candidate_stage(candidate_id, 'Interview')
            elif status_value == 'Rejected':
                update_candidate_stage(candidate_id, 'Rejected')
            elif status_value == 'Hold':
                update_candidate_stage(candidate_id, 'Interview Hold')
            flash('Interview result submitted successfully!', 'success')
        else:
            flash('Error submitting interview result!', 'error')
            
    except Exception as e:
        logging.error(f"Error submitting interview: {e}")
        flash('Error submitting interview result!', 'error')
    
    return redirect(request.referrer)

@app.route('/offer/<int:cand_id>')
def offer_form(cand_id):
    """Show offer form for a candidate"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('offer_form.html', candidate=candidate.iloc[0].to_dict())

@app.route('/offer', methods=['POST'])
def create_offer():
    """Create offer details"""
    try:
        candidate_id = int(request.form['candidate_id'])
        
        offer_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'offers.csv')),
            'candidate_id': candidate_id,
            'job_title': request.form['job_title'],
            'salary': request.form['salary'],
            'joining_date': request.form['joining_date'],
            'department': request.form['department'],
            'location': request.form['location'],
            'benefits': request.form['benefits'],
            'offer_letter_generated': 'Yes',
            'offer_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Sent'
        }
        
        if append_to_csv(offer_data, os.path.join(CSV_FOLDER, 'offers.csv')):
            update_candidate_stage(candidate_id, 'Offer')
            flash('Offer created successfully!', 'success')
        else:
            flash('Error creating offer!', 'error')
            
    except Exception as e:
        logging.error(f"Error creating offer: {e}")
        flash('Error creating offer!', 'error')
    
    return redirect(request.referrer)

@app.route('/offer-letter/<int:cand_id>')
def generate_offer_letter(cand_id):
    """Generate offer letter HTML"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    
    candidate = candidates_df[candidates_df['id'] == cand_id]
    offer = offers_df[offers_df['candidate_id'] == cand_id]
    
    if candidate.empty or offer.empty:
        flash('Candidate or offer not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('offer_letter.html', 
                         candidate=candidate.iloc[0].to_dict(),
                         offer=offer.iloc[0].to_dict())

@app.route('/onboarding/<int:cand_id>')
def onboarding(cand_id):
    """Show onboarding page for employee"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    
    candidate = candidates_df[candidates_df['id'] == cand_id]
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    candidate_data = candidate.iloc[0].to_dict()
    
    # Fetch requisition information for this candidate (original position)
    if candidate_data.get('requisition_id') and candidate_data.get('requisition_id') != '0':
        requisition_data = requisitions_df[requisitions_df['id'] == int(candidate_data['requisition_id'])]
        if not requisition_data.empty:
            requisition = requisition_data.iloc[0].to_dict()
            # Add requisition information to candidate data
            candidate_data.update({
                'position': requisition.get('position_title', 'N/A'),
                'requisition_department': requisition.get('department', 'N/A')
            })
    
    # Fetch offer information for this candidate
    offer_data = offers_df[offers_df['candidate_id'] == cand_id]
    if not offer_data.empty:
        offer = offer_data.iloc[0].to_dict()
        # Add offer information to candidate data
        candidate_data.update({
            'department': offer.get('department', 'N/A'),
            'job_title': offer.get('job_title', 'N/A'),
            'joining_date': offer.get('joining_date', 'N/A'),
            'location': offer.get('location', 'N/A'),
            'salary': offer.get('salary', 'N/A'),
            'benefits': offer.get('benefits', 'N/A')
        })
    
    onboarding_record = onboarding_df[onboarding_df['candidate_id'] == cand_id]
    onboarding_data = onboarding_record.iloc[0].to_dict() if not onboarding_record.empty else {}
    
    return render_template('onboarding.html', 
                         candidate=candidate_data,
                         onboarding=onboarding_data)

@app.route('/onboarding', methods=['POST'])
def update_onboarding():
    """Update onboarding checklist"""
    try:
        candidate_id = int(request.form['candidate_id'])
        # Handle signed offer letter upload (optional)
        signed_offer_filename = None
        try:
            if 'signed_offer' in request.files:
                file = request.files['signed_offer']
                if file and file.filename and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                    signed_offer_filename = unique_filename
        except Exception as e:
            logging.error(f"Error saving signed offer: {e}")

        # If no new file uploaded, try to reuse latest from onboarding history
        if not signed_offer_filename:
            try:
                existing_onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
                existing_rows = existing_onboarding_df[existing_onboarding_df['candidate_id'] == candidate_id]
                if not existing_rows.empty and 'signed_offer_filename' in existing_rows.columns:
                    last_row = existing_rows.iloc[-1]
                    prev_file = last_row.get('signed_offer_filename', '')
                    if isinstance(prev_file, str) and prev_file:
                        signed_offer_filename = prev_file
            except Exception:
                pass

        onboarding_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'onboarding.csv')),
            'candidate_id': candidate_id,
            'documents_verified': request.form.get('documents_verified', 'No'),
            'laptop_assigned': request.form.get('laptop_assigned', 'No'),
            'id_card_issued': request.form.get('id_card_issued', 'No'),
            'workspace_assigned': request.form.get('workspace_assigned', 'No'),
            'orientation_completed': request.form.get('orientation_completed', 'No'),
            'system_access_provided': request.form.get('system_access_provided', 'No'),
            'comments': request.form['comments'],
            'onboarding_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hr_representative': request.form['hr_representative'],
            'signed_offer_filename': signed_offer_filename or ''
        }
        
        if append_to_csv(onboarding_data, os.path.join(CSV_FOLDER, 'onboarding.csv')):
            update_candidate_stage(candidate_id, 'Onboarded')
            flash('Onboarding updated successfully!', 'success')
        else:
            flash('Error updating onboarding!', 'error')
            
    except Exception as e:
        logging.error(f"Error updating onboarding: {e}")
        flash('Error updating onboarding!', 'error')
    
    return redirect(request.referrer)

@app.route('/resignation/<int:cand_id>')
def resignation_form(cand_id):
    """Show resignation form"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))

    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Employee not found!', 'error')
        return redirect(url_for('dashboard'))

    candidate_dict = candidate.iloc[0].to_dict()

    # Enrich department from offer
    offer_row = offers_df[offers_df['candidate_id'] == cand_id]
    if not offer_row.empty:
        offer = offer_row.iloc[0].to_dict()
        candidate_dict['department'] = offer.get('department', candidate_dict.get('department', 'N/A'))

    # Preload latest resignation (if any)
    existing = None
    res_rows = resignations_df[resignations_df['candidate_id'] == cand_id]
    if not res_rows.empty:
        try:
            res_rows = res_rows.sort_values(by='resignation_date')
        except Exception:
            pass
        existing = res_rows.iloc[-1].to_dict()
    
    return render_template('resignation.html', candidate=candidate_dict, existing=existing)

@app.route('/resignation', methods=['POST'])
def submit_resignation():
    """Record resignation"""
    try:
        candidate_id = int(request.form['candidate_id'])

        # Compute completion status from checklist
        exit_interview = request.form.get('exit_interview_completed', 'No')
        laptop_ret = request.form.get('laptop_returned', 'No')
        id_card_ret = request.form.get('id_card_returned', 'No')
        clearance = request.form.get('clearance_completed', 'No')
        final_settlement = request.form.get('final_settlement', 'Pending')
        completion_status = 'Completed' if (exit_interview == 'Yes' and laptop_ret == 'Yes' and id_card_ret == 'Yes' and clearance == 'Yes' and final_settlement == 'Completed') else 'In Progress'

        # Optional new fields: notice period and end date
        notice_period_days = request.form.get('notice_period_days', '')
        notice_period_end_date = request.form.get('notice_period_end_date', '')

        # Handle resignation documents upload
        def save_optional_upload(field_name):
            try:
                if field_name in request.files:
                    f = request.files[field_name]
                    if f and f.filename and f.filename != '' and allowed_file(f.filename):
                        filename = secure_filename(f.filename)
                        unique_name = f"{uuid.uuid4()}_{filename}"
                        f.save(os.path.join(UPLOAD_FOLDER, unique_name))
                        return unique_name
            except Exception as e:
                logging.error(f"Error saving file for {field_name}: {e}")
            return ''

        resignation_letter_file = save_optional_upload('resignation_letter')
        acceptance_letter_file = save_optional_upload('resignation_acceptance_letter')
        relieving_letter_file = save_optional_upload('relieving_letter')

        resignation_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'resignations.csv')),
            'candidate_id': candidate_id,
            'resignation_date': request.form['resignation_date'],
            'last_working_date': request.form['last_working_date'],
            'reason': request.form['reason'],
            'exit_interview_completed': exit_interview,
            'laptop_returned': laptop_ret,
            'id_card_returned': id_card_ret,
            'clearance_completed': clearance,
            'final_settlement': final_settlement,
            'comments': request.form['comments'],
            'hr_representative': request.form['hr_representative'],
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completion_status': completion_status,
            'notice_period_days': notice_period_days,
            'notice_period_end_date': notice_period_end_date,
            'resignation_letter_filename': resignation_letter_file,
            'acceptance_letter_filename': acceptance_letter_file,
            'relieving_letter_filename': relieving_letter_file,
        }
        
        if append_to_csv(resignation_data, os.path.join(CSV_FOLDER, 'resignations.csv')):
            update_candidate_stage(candidate_id, 'Resigned')
            flash('Resignation recorded successfully!', 'success')
        else:
            flash('Error recording resignation!', 'error')
            
    except Exception as e:
        logging.error(f"Error recording resignation: {e}")
        flash('Error recording resignation!', 'error')
    
    return redirect(request.referrer)

# New separate page routes
@app.route('/requisitions-page')
def requisitions_page():
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    return render_template('requisitions.html', requisitions=requisitions_df.to_dict('records'))

@app.route('/candidates-page')
def candidates_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    return render_template('candidates.html', candidates=candidates_df.to_dict('records'))

@app.route('/screening-page')
def screening_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    # Filter candidates at Applied stage
    applied_candidates = candidates_df[candidates_df['stage'] == 'Applied'].to_dict('records')
    return render_template('screening.html', candidates=applied_candidates)

@app.route('/interviews-page')
def interviews_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    # Filter candidates at Screening stage (ready for interview)
    screening_candidates = candidates_df[candidates_df['stage'] == 'Screening'].to_dict('records')
    return render_template('interviews.html', candidates=screening_candidates)

@app.route('/offers-page')
def offers_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    # Filter candidates at Interview stage (ready for offer)
    interview_candidates = candidates_df[candidates_df['stage'] == 'Interview'].to_dict('records')
    # Also get candidates with offers
    offer_candidates = candidates_df[candidates_df['stage'] == 'Offer'].to_dict('records')
    return render_template('offers.html', candidates=interview_candidates, offer_candidates=offer_candidates)

@app.route('/onboarding-page')
def onboarding_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    
    # Filter candidates at Offer stage (ready for onboarding)
    offer_candidates = candidates_df[candidates_df['stage'] == 'Offer'].to_dict('records')
    # Also get recently onboarded
    onboarded_candidates = candidates_df[candidates_df['stage'] == 'Onboarded'].to_dict('records')
    
    # Add requisition and offer information to candidates
    for candidate in offer_candidates + onboarded_candidates:
        # Fetch requisition information (original position)
        if candidate.get('requisition_id') and candidate.get('requisition_id') != '0':
            requisition_data = requisitions_df[requisitions_df['id'] == int(candidate['requisition_id'])]
            if not requisition_data.empty:
                requisition = requisition_data.iloc[0].to_dict()
                candidate.update({
                    'position': requisition.get('position_title', 'N/A'),
                    'requisition_department': requisition.get('department', 'N/A')
                })
        
        # Fetch offer information
        offer_data = offers_df[offers_df['candidate_id'] == candidate['id']]
        if not offer_data.empty:
            offer = offer_data.iloc[0].to_dict()
            candidate.update({
                'department': offer.get('department', 'N/A'),
                'job_title': offer.get('job_title', 'N/A'),
                'joining_date': offer.get('joining_date', 'N/A'),
                'location': offer.get('location', 'N/A'),
                'salary': offer.get('salary', 'N/A'),
                'benefits': offer.get('benefits', 'N/A'),
                'offer_date': offer.get('offer_date', 'N/A')
            })
    
    # Add onboarding information to onboarded candidates
    for candidate in onboarded_candidates:
        onboarding_data = onboarding_df[onboarding_df['candidate_id'] == candidate['id']]
        if not onboarding_data.empty:
            onboarding = onboarding_data.iloc[0].to_dict()
            candidate.update({
                'onboarding_date': onboarding.get('onboarding_date', 'N/A'),
                'hr_representative': onboarding.get('hr_representative', 'N/A')
            })
    
    return render_template('onboarding_list.html', candidates=offer_candidates, onboarded_candidates=onboarded_candidates)

@app.route('/employees-page')
def employees_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    
    # Filter employees (onboarded candidates)
    employees = candidates_df[candidates_df['stage'] == 'Onboarded'].to_dict('records')
    
    # Add offer and requisition information to employees
    for employee in employees:
        # Fetch requisition information (original position)
        if employee.get('requisition_id') and employee.get('requisition_id') != '0':
            requisition_data = requisitions_df[requisitions_df['id'] == int(employee['requisition_id'])]
            if not requisition_data.empty:
                requisition = requisition_data.iloc[0].to_dict()
                employee.update({
                    'position': requisition.get('position_title', 'N/A'),
                    'requisition_department': requisition.get('department', 'N/A')
                })
        
        # Fetch offer information
        offer_data = offers_df[offers_df['candidate_id'] == employee['id']]
        if not offer_data.empty:
            offer = offer_data.iloc[0].to_dict()
            employee.update({
                'department': offer.get('department', 'N/A'),
                'job_title': offer.get('job_title', 'N/A'),
                'joining_date': offer.get('joining_date', 'N/A'),
                'location': offer.get('location', 'N/A'),
                'salary': offer.get('salary', 'N/A'),
                'benefits': offer.get('benefits', 'N/A'),
                'offer_date': offer.get('offer_date', 'N/A')
            })
        # Attach latest resignation document filenames if resigned
        if employee.get('stage') == 'Resigned':
            resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))
            res_rows = resignations_df[resignations_df['candidate_id'] == employee['id']]
            if not res_rows.empty:
                try:
                    res_rows = res_rows.sort_values(by='updated_at')
                except Exception:
                    pass
                latest = res_rows.iloc[-1].to_dict()
                employee.update({
                    'resignation_letter_filename': latest.get('resignation_letter_filename', ''),
                    'acceptance_letter_filename': latest.get('acceptance_letter_filename', ''),
                    'relieving_letter_filename': latest.get('relieving_letter_filename', ''),
                })
    
    return render_template('employees.html', employees=employees)

@app.route('/resignations-page')
def resignations_page():
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))

    # Filter resigned candidates
    resigned_candidates = candidates_df[candidates_df['stage'] == 'Resigned'].to_dict('records')

    # Enrich resigned candidates with offer department and latest resignation info
    for cand in resigned_candidates:
        offer_row = offers_df[offers_df['candidate_id'] == cand['id']]
        if not offer_row.empty:
            offer = offer_row.iloc[0].to_dict()
            cand['department'] = offer.get('department', cand.get('department', 'N/A'))

        res_rows = resignations_df[resignations_df['candidate_id'] == cand['id']]
        if not res_rows.empty:
            try:
                res_rows = res_rows.sort_values(by='resignation_date')
            except Exception:
                pass
            latest = res_rows.iloc[-1].to_dict()
            cand['resignation_date'] = latest.get('resignation_date', 'N/A')
            cand['last_working_date'] = latest.get('last_working_date', 'N/A')
            cand['resignation_reason'] = latest.get('reason', 'N/A')

    # Also get active employees for resignation processing and enrich department from offer
    active_employees = candidates_df[candidates_df['stage'] == 'Onboarded'].to_dict('records')
    for emp in active_employees:
        offer_row = offers_df[offers_df['candidate_id'] == emp['id']]
        if not offer_row.empty:
            offer = offer_row.iloc[0].to_dict()
            emp['department'] = offer.get('department', emp.get('department', 'N/A'))

    return render_template('resignations_list.html', resigned_candidates=resigned_candidates, active_employees=active_employees)

@app.route('/resignation-details/<int:cand_id>')
def resignation_detail(cand_id):
    """Show resignation details and history for an employee"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))

    candidate_df = candidates_df[candidates_df['id'] == cand_id]
    if candidate_df.empty:
        flash('Employee not found!', 'error')
        return redirect(url_for('resignations_page'))

    candidate = candidate_df.iloc[0].to_dict()

    # Enrich with offer details (department and job_title)
    offer_row = offers_df[offers_df['candidate_id'] == cand_id]
    if not offer_row.empty:
        offer = offer_row.iloc[0].to_dict()
        candidate['department'] = offer.get('department', candidate.get('department', 'N/A'))
        candidate['job_title'] = offer.get('job_title', candidate.get('job_title', 'N/A'))

    # Build resignation history
    res_rows = resignations_df[resignations_df['candidate_id'] == cand_id]
    history = []
    if not res_rows.empty:
        try:
            res_rows = res_rows.sort_values(by='resignation_date')
        except Exception:
            pass
        history = res_rows.to_dict('records')
    latest = history[-1] if history else None

    return render_template('resignation_detail.html', candidate=candidate, resignation=latest, resignation_history=history)

# Resignation documents routes
@app.route('/resignation-doc/<int:cand_id>/<doc_type>/download')
def download_resignation_doc(cand_id, doc_type):
    """Download resignation-related documents: resignation_letter | acceptance_letter | relieving_letter"""
    valid_types = {
        'resignation_letter': 'resignation_letter_filename',
        'acceptance_letter': 'acceptance_letter_filename',
        'relieving_letter': 'relieving_letter_filename',
    }
    if doc_type not in valid_types:
        flash('Invalid document type', 'error')
        return redirect(request.referrer or url_for('resignation_detail', cand_id=cand_id))

    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))
    rows = resignations_df[resignations_df['candidate_id'] == cand_id]
    if rows.empty or valid_types[doc_type] not in rows.columns:
        flash('Document not found', 'error')
        return redirect(request.referrer or url_for('resignation_detail', cand_id=cand_id))
    filename = rows.iloc[-1].get(valid_types[doc_type], '')
    if not filename:
        flash('Document not found', 'error')
        return redirect(request.referrer or url_for('resignation_detail', cand_id=cand_id))
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)
    except FileNotFoundError:
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('resignation_detail', cand_id=cand_id))

@app.route('/resignation-doc/<int:cand_id>/<doc_type>/preview')
def preview_resignation_doc(cand_id, doc_type):
    valid_types = {
        'resignation_letter': 'resignation_letter_filename',
        'acceptance_letter': 'acceptance_letter_filename',
        'relieving_letter': 'relieving_letter_filename',
    }
    if doc_type not in valid_types:
        return "Invalid document type", 400
    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))
    rows = resignations_df[resignations_df['candidate_id'] == cand_id]
    if rows.empty or valid_types[doc_type] not in rows.columns:
        return "Document not found", 404
    filename = rows.iloc[-1].get(valid_types[doc_type], '')
    if not filename:
        return "Document not found", 404
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "Document not found", 404
    file_ext = filename.lower().split('.')[-1]
    content_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
    }
    return send_file(file_path, mimetype=content_types.get(file_ext, 'application/octet-stream'), as_attachment=False)

@app.route('/add-employee-direct', methods=['POST'])
def add_employee_direct():
    """Add employee directly to the system (bypass recruitment process)"""
    try:
        employee_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'candidates.csv')),
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'department': request.form['department'],
            'position': request.form['position'],
            'join_date': request.form['join_date'],
            'experience': request.form.get('experience', '0'),
            'salary': request.form.get('salary', ''),
            'skills': request.form.get('skills', ''),
            'stage': 'Onboarded',
            'applied_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'requisition_id': '0',  # Direct hire, no requisition
            'resume_filename': '',
            'current_salary': request.form.get('salary', ''),
            'expected_salary': request.form.get('salary', ''),
            'notice_period': '0',
            'source': request.form.get('source', 'Direct')
        }
        
        if append_to_csv(employee_data, os.path.join(CSV_FOLDER, 'candidates.csv')):
            flash('Employee added successfully!', 'success')
        else:
            flash('Error adding employee!', 'error')
            
    except Exception as e:
        logging.error(f"Error adding employee: {e}")
        flash('Error adding employee!', 'error')
    
    return redirect(url_for('employees_page'))

@app.route('/candidate/<int:cand_id>')
def candidate_detail(cand_id):
    """Show candidate details"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    screening_df = read_csv_safe(os.path.join(CSV_FOLDER, 'screening.csv'))
    interviews_df = read_csv_safe(os.path.join(CSV_FOLDER, 'interviews.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    
    candidate_data = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate_data.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('candidates_page'))
    
    candidate = candidate_data.to_dict('records')[0]
    
    # Normalize candidate_id columns to numeric for reliable filtering
    try:
        if not screening_df.empty:
            screening_df['candidate_id'] = pd.to_numeric(screening_df['candidate_id'], errors='coerce')
        if not interviews_df.empty:
            interviews_df['candidate_id'] = pd.to_numeric(interviews_df['candidate_id'], errors='coerce')
    except Exception:
        pass
    # Fetch screening attempts (history) for this candidate
    screening_rows = screening_df[screening_df['candidate_id'] == cand_id]
    screening_history = []
    if not screening_rows.empty:
        try:
            screening_rows = screening_rows.sort_values(by='screening_date')
        except Exception:
            pass
        screening_history = screening_rows.to_dict('records')
    latest_screening = screening_history[-1] if screening_history else None
    
    # Fetch interview attempts (history) for this candidate
    interview_rows = interviews_df[interviews_df['candidate_id'] == cand_id]
    interview_history = []
    if not interview_rows.empty:
        try:
            interview_rows = interview_rows.sort_values(by='interview_date')
        except Exception:
            pass
        interview_history = interview_rows.to_dict('records')
    latest_interview = interview_history[-1] if interview_history else None
    
    # Fetch offer information for this candidate (latest)
    offer_rows = offers_df[offers_df['candidate_id'] == cand_id]
    offer = offer_rows.iloc[0].to_dict() if not offer_rows.empty else None
    
    # Fetch requisition information for this candidate
    requisition = None
    if candidate.get('requisition_id') and candidate.get('requisition_id') != '0':
        requisition_data = requisitions_df[requisitions_df['id'] == int(candidate['requisition_id'])]
        if not requisition_data.empty:
            requisition = requisition_data.iloc[0].to_dict()
    
    return render_template(
        'candidate_detail.html',
        candidate=candidate,
        screening=latest_screening,
        screening_history=screening_history,
        interview=latest_interview,
        interview_history=interview_history,
        offer=offer,
        requisition=requisition,
    )

@app.route('/employee/<int:emp_id>')
def employee_detail(emp_id):
    """Show employee details"""
    candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
    offers_df = read_csv_safe(os.path.join(CSV_FOLDER, 'offers.csv'))
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    
    employee_data = candidates_df[(candidates_df['id'] == emp_id) & (candidates_df['stage'] == 'Onboarded')]
    
    if employee_data.empty:
        flash('Employee not found!', 'error')
        return redirect(url_for('employees_page'))
    
    employee = employee_data.to_dict('records')[0]
    
    # Fetch requisition information for this employee (original position)
    if employee.get('requisition_id') and employee.get('requisition_id') != '0':
        requisition_data = requisitions_df[requisitions_df['id'] == int(employee['requisition_id'])]
        if not requisition_data.empty:
            requisition = requisition_data.iloc[0].to_dict()
            # Add requisition information to employee data
            employee.update({
                'position': requisition.get('position_title', 'N/A'),
                'requisition_department': requisition.get('department', 'N/A')
            })
    
    # Fetch offer information for this employee
    offer_data = offers_df[offers_df['candidate_id'] == emp_id]
    if not offer_data.empty:
        offer = offer_data.iloc[0].to_dict()
        # Add offer information to employee data
        employee.update({
            'job_title': offer.get('job_title', 'N/A'),
            'department': offer.get('department', 'N/A'),
            'salary': offer.get('salary', 'N/A'),
            'joining_date': offer.get('joining_date', 'N/A'),
            'location': offer.get('location', 'N/A'),
            'benefits': offer.get('benefits', 'N/A'),
            'offer_date': offer.get('offer_date', 'N/A')
        })
    
    # Fetch latest onboarding info to attach signed offer filename
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    onboarding_rows = onboarding_df[onboarding_df['candidate_id'] == emp_id]
    if not onboarding_rows.empty and 'signed_offer_filename' in onboarding_rows.columns:
        try:
            onboarding_rows = onboarding_rows.sort_values(by='onboarding_date')
        except Exception:
            pass
        latest_onboarding = onboarding_rows.iloc[-1].to_dict()
        employee['signed_offer_filename'] = latest_onboarding.get('signed_offer_filename', '')

    # If resigned, attach resignation document filenames
    resignations_df = read_csv_safe(os.path.join(CSV_FOLDER, 'resignations.csv'))
    res_rows = resignations_df[resignations_df['candidate_id'] == emp_id]
    if not res_rows.empty:
        try:
            res_rows = res_rows.sort_values(by='updated_at')
        except Exception:
            pass
        latest_res = res_rows.iloc[-1].to_dict()
        employee['stage'] = 'Resigned'
        employee['resignation_letter_filename'] = latest_res.get('resignation_letter_filename', '')
        employee['acceptance_letter_filename'] = latest_res.get('acceptance_letter_filename', '')
        employee['relieving_letter_filename'] = latest_res.get('relieving_letter_filename', '')
    
    return render_template('employee_detail.html', employee=employee)

# Signed offer letter routes
@app.route('/signed-offer/<int:cand_id>/download')
def download_signed_offer(cand_id):
    """Download the signed offer letter for the candidate"""
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    rows = onboarding_df[onboarding_df['candidate_id'] == cand_id]
    if rows.empty or 'signed_offer_filename' not in rows.columns:
        flash('No signed offer on file for this employee.', 'error')
        return redirect(request.referrer or url_for('employee_detail', emp_id=cand_id))
    filename = rows.iloc[-1].get('signed_offer_filename', '')
    if not filename:
        flash('No signed offer on file for this employee.', 'error')
        return redirect(request.referrer or url_for('employee_detail', emp_id=cand_id))
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)
    except FileNotFoundError:
        flash('Signed offer file not found!', 'error')
        return redirect(request.referrer or url_for('employee_detail', emp_id=cand_id))

@app.route('/signed-offer/<int:cand_id>/preview')
def preview_signed_offer(cand_id):
    """Inline preview for the signed offer letter"""
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    rows = onboarding_df[onboarding_df['candidate_id'] == cand_id]
    if rows.empty or 'signed_offer_filename' not in rows.columns:
        return "Signed offer not found", 404
    filename = rows.iloc[-1].get('signed_offer_filename', '')
    if not filename:
        return "Signed offer not found", 404

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "Signed offer not found", 404

    file_ext = filename.lower().split('.')[-1]
    content_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
    }
    content_type = content_types.get(file_ext, 'application/octet-stream')
    return send_file(file_path, mimetype=content_type, as_attachment=False)

# Helper function to read CSV data as dictionaries for compatibility
def read_csv_data(csv_file_path):
    """Read CSV file and return as list of dictionaries"""
    df = read_csv_safe(csv_file_path)
    return df.to_dict('records')

# Admin download routes
@app.route('/download/<csv_name>')
def download_csv(csv_name):
    """Download CSV files for admin"""
    allowed_csvs = ['requisitions', 'candidates', 'screening', 'interviews', 'offers', 'onboarding', 'resignations']
    if csv_name not in allowed_csvs:
        flash('Invalid CSV file!', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        csv_path = os.path.join(CSV_FOLDER, f'{csv_name}.csv')
        return send_file(csv_path, as_attachment=True, download_name=f'{csv_name}.csv')
    except FileNotFoundError:
        flash('CSV file not found!', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
