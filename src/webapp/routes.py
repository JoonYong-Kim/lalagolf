
from flask import render_template, current_app, jsonify, request, session, redirect, url_for, flash
from src.webapp import app
from src.db_loader import get_db_connection, save_round_data
from src.data_parser import parse_file, analyze_shots_and_stats # Import analyze_shots_and_stats
import os
from datetime import datetime
from functools import wraps

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def round_list():
    db_config = current_app.config['DB_CONFIG']
    conn = get_db_connection(db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM rounds WHERE score IS NOT NULL ORDER BY playdate ASC")
    rounds = cursor.fetchall()

    cursor.close()
    conn.close()

    # Prepare data for the chart
    labels = [r['playdate'].strftime('%Y-%m-%d') for r in rounds]
    data = [r['score'] for r in rounds]

    return render_template('rounds.html', rounds=rounds, labels=labels, data=data)

@app.route('/round/<int:round_id>')
def round_detail(round_id):
    db_config = current_app.config['DB_CONFIG']
    conn = get_db_connection(db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM rounds WHERE id = %s", (round_id,))
    round_info = cursor.fetchone()

    cursor.execute("SELECT * FROM holes WHERE roundid = %s ORDER BY holenum", (round_id,))
    holes = cursor.fetchall()

    cursor.execute("SELECT * FROM shots WHERE roundid = %s ORDER BY id", (round_id,))
    shots = cursor.fetchall()

    # Map 'feelgrade' from DB to 'feel' for data_parser compatibility
    for shot in shots:
        if 'feelgrade' in shot:
            shot['feel'] = shot['feelgrade']
            del shot['feelgrade']
        if 'retgrade' in shot:
            shot['result'] = shot['retgrade']
            del shot['retgrade']
        if 'shotplace' in shot:
            shot['on'] = shot['shotplace']
            del shot['shotplace']

        if shot['error']:
            tmp = shot['error'] / shot['distance']
            shot['eresult'] = 'A' if tmp < 0.05 else 'B' if tmp < 0.1 else 'C'

    # Prepare data for club analysis chart
    club_counts = {}
    for shot in shots:
        club = shot['club']
        if club in club_counts:
            club_counts[club] += 1
        else:
            club_counts[club] = 1
    
    club_labels = list(club_counts.keys())
    club_data = list(club_counts.values())

    # Analyze detailed shot statistics
    detailed_shot_stats = analyze_shots_and_stats(shots)

    cursor.close()
    conn.close()

    return render_template('round_detail.html', round_info=round_info, holes=holes, shots=shots, club_labels=club_labels, club_data=club_data, detailed_shot_stats=detailed_shot_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = current_app.config['WEBAPP_USERS']

        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('upload_round'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/upload_round', methods=['GET', 'POST'])
@login_required
def upload_round():
    if request.method == 'POST':
        raw_data = None
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            raw_data = file.read().decode('utf-8')
        elif 'raw_text' in request.form and request.form['raw_text'] != '':
            raw_data = request.form['raw_text']

        if raw_data:
            # Save raw data to a temporary file for parse_file
            temp_file_path = "/tmp/uploaded_golf_data.txt"
            with open(temp_file_path, 'w') as f:
                f.write(raw_data)
            
            try:
                parsed_data, scores_and_stats = parse_file(temp_file_path)
                session['parsed_data'] = parsed_data
                session['scores_and_stats'] = scores_and_stats
                session['raw_data_content'] = raw_data # Store raw content for saving to file later
                return redirect(url_for('review_round'))
            except Exception as e:
                return render_template('upload_form.html', error=f"Parsing error: {e}")
        else:
            return render_template('upload_form.html', error="No file or text provided.")

    return render_template('upload_form.html')

@app.route('/review_round', methods=['GET', 'POST'])
@login_required
def review_round():
    parsed_data = session.get('parsed_data')
    scores_and_stats = session.get('scores_and_stats')
    raw_data_content = session.get('raw_data_content')

    if not parsed_data or not scores_and_stats or not raw_data_content:
        return redirect(url_for('upload_round')) # Redirect if no data in session

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            try:
                # Save raw data to file based on tee-off time
                tee_off_time_str = parsed_data['tee_off_time']
                # Assuming tee_off_time_str is in 'YYYY-MM-DD HH:MM' format
                tee_off_datetime = datetime.strptime(tee_off_time_str, '%Y-%m-%d %H:%M')
                year_dir = tee_off_datetime.strftime('%Y')
                file_name = tee_off_datetime.strftime('%Y%m%d.txt')
                
                save_dir = os.path.join('data', year_dir)
                os.makedirs(save_dir, exist_ok=True)
                
                final_file_path = os.path.join(save_dir, file_name)
                with open(final_file_path, 'w') as f:
                    f.write(raw_data_content)

                # Save parsed data to database
                db_config = current_app.config['DB_CONFIG']
                save_round_data(db_config, parsed_data, scores_and_stats)
                
                session.pop('parsed_data', None)
                session.pop('scores_and_stats', None)
                session.pop('raw_data_content', None)
                
                return redirect(url_for('round_list')) # Redirect to list after saving
            except Exception as e:
                return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats, error=f"Save error: {e}")
        elif request.form.get('action') == 'cancel':
            session.pop('parsed_data', None)
            session.pop('scores_and_stats', None)
            session.pop('raw_data_content', None)
            return redirect(url_for('upload_round'))

    return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats)
