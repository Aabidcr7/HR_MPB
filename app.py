import os
import csv
import pandas as pd
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, make_response
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
    """Main dashboard showing requisitions"""
    requisitions_df = read_csv_safe(os.path.join(CSV_FOLDER, 'requisitions.csv'))
    return render_template('dashboard.html', requisitions=requisitions_df.to_dict('records'))

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
            'notice_period': request.form.get('notice_period', '')
        }
        
        if append_to_csv(candidate_data, os.path.join(CSV_FOLDER, 'candidates.csv')):
            flash('Candidate added successfully!', 'success')
        else:
            flash('Error adding candidate!', 'error')
            
    except Exception as e:
        logging.error(f"Error adding candidate: {e}")
        flash('Error adding candidate!', 'error')
    
    return redirect(url_for('requisition_detail', req_id=req_id))

@app.route('/candidates/bulk-upload', methods=['POST'])
def bulk_upload_candidates():
    """Handle CSV upload to bulk-add candidates"""
    if 'csv_file' not in request.files:
        flash('No file selected!', 'error')
        return redirect(request.referrer)
    
    file = request.files['csv_file']
    if not file.filename or file.filename == '' or not file.filename.endswith('.csv'):
        flash('Please select a valid CSV file!', 'error')
        return redirect(request.referrer)
    
    try:
        # Read uploaded CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        candidates_df = read_csv_safe(os.path.join(CSV_FOLDER, 'candidates.csv'))
        
        count = 0
        for row in csv_input:
            candidate_data = {
                'id': get_next_id(os.path.join(CSV_FOLDER, 'candidates.csv')) + count,
                'requisition_id': row.get('requisition_id', ''),
                'name': row.get('name', ''),
                'email': row.get('email', ''),
                'phone': row.get('phone', ''),
                'experience': row.get('experience', ''),
                'skills': row.get('skills', ''),
                'resume_filename': '',
                'stage': 'Applied',
                'applied_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'current_salary': row.get('current_salary', ''),
                'expected_salary': row.get('expected_salary', ''),
                'notice_period': row.get('notice_period', '')
            }
            
            new_row = pd.DataFrame([candidate_data])
            candidates_df = pd.concat([candidates_df, new_row], ignore_index=True)
            count += 1
        
        if write_csv_safe(candidates_df, os.path.join(CSV_FOLDER, 'candidates.csv')):
            flash(f'{count} candidates uploaded successfully!', 'success')
        else:
            flash('Error uploading candidates!', 'error')
            
    except Exception as e:
        logging.error(f"Error in bulk upload: {e}")
        flash('Error processing CSV file!', 'error')
    
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
            # If shortlisted, move to Interview stage
            if request.form['status'] == 'Shortlisted':
                update_candidate_stage(candidate_id, 'Screening')
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
            # If shortlisted, move to Offer stage
            if request.form['status'] == 'Shortlisted':
                update_candidate_stage(candidate_id, 'Interview')
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
    onboarding_df = read_csv_safe(os.path.join(CSV_FOLDER, 'onboarding.csv'))
    
    candidate = candidates_df[candidates_df['id'] == cand_id]
    if candidate.empty:
        flash('Candidate not found!', 'error')
        return redirect(url_for('dashboard'))
    
    onboarding_record = onboarding_df[onboarding_df['candidate_id'] == cand_id]
    onboarding_data = onboarding_record.iloc[0].to_dict() if not onboarding_record.empty else {}
    
    return render_template('onboarding.html', 
                         candidate=candidate.iloc[0].to_dict(),
                         onboarding=onboarding_data)

@app.route('/onboarding', methods=['POST'])
def update_onboarding():
    """Update onboarding checklist"""
    try:
        candidate_id = int(request.form['candidate_id'])
        
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
            'hr_representative': request.form['hr_representative']
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
    candidate = candidates_df[candidates_df['id'] == cand_id]
    
    if candidate.empty:
        flash('Employee not found!', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('resignation.html', candidate=candidate.iloc[0].to_dict())

@app.route('/resignation', methods=['POST'])
def submit_resignation():
    """Record resignation"""
    try:
        candidate_id = int(request.form['candidate_id'])
        
        resignation_data = {
            'id': get_next_id(os.path.join(CSV_FOLDER, 'resignations.csv')),
            'candidate_id': candidate_id,
            'resignation_date': request.form['resignation_date'],
            'last_working_date': request.form['last_working_date'],
            'reason': request.form['reason'],
            'exit_interview_completed': request.form.get('exit_interview_completed', 'No'),
            'laptop_returned': request.form.get('laptop_returned', 'No'),
            'id_card_returned': request.form.get('id_card_returned', 'No'),
            'clearance_completed': request.form.get('clearance_completed', 'No'),
            'final_settlement': request.form.get('final_settlement', 'Pending'),
            'comments': request.form['comments'],
            'hr_representative': request.form['hr_representative']
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
