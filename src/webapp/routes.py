
from flask import render_template, current_app, jsonify, request, session, redirect, url_for, flash
from src.webapp import app
from src.db_loader import get_db_connection, save_round_data, delete_round_data, init_connection_pool, get_filtered_rounds, get_yearly_round_statistics
from src.data_parser import parse_file, analyze_shots_and_stats # Import analyze_shots_and_stats
import os
from datetime import datetime
from functools import wraps
import json

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    if 'DB_CONFIG' in current_app.config:
        init_connection_pool(current_app.config['DB_CONFIG'])

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    selected_year = request.args.get('year', 'all')

    query = "SELECT *, gir FROM rounds WHERE score IS NOT NULL"
    params = []

    if selected_year != 'all':
        query += " AND YEAR(playdate) = %s"
        params.append(selected_year)
    
    query += " ORDER BY playdate ASC"

    cursor.execute(query, params)
    rounds = cursor.fetchall()

    labels = [r['playdate'].strftime('%Y-%m-%d') for r in rounds]
    data = [r['score'] for r in rounds]

    cursor.execute("SELECT DISTINCT YEAR(playdate) AS year FROM rounds ORDER BY year DESC")
    unique_years = [row['year'] for row in cursor.fetchall()]

    cursor.close() 
    conn.close()  

    yearly_stats = get_yearly_round_statistics()

    return render_template('index.html', 
                           rounds=rounds, 
                           labels=labels, 
                           data=data, 
                           selected_year=selected_year,
                           unique_years=unique_years,
                           yearly_stats=yearly_stats)

@app.route('/rounds')
def list_rounds():
    db_config = current_app.config['DB_CONFIG']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    current_year = datetime.now().year
    selected_year = request.args.get('year', 'all')
    selected_golf_course = request.args.get('golf_course', 'all')
    selected_companion = request.args.get('companion', 'all')
    sort_by = request.args.get('sort_by', 'playdate')
    sort_order = request.args.get('sort_order', 'ASC')
    search_query = request.args.get('search_query')

    rounds = get_filtered_rounds(year=selected_year, golf_course=selected_golf_course, companion=selected_companion, sort_by=sort_by, sort_order=sort_order, search_query=search_query)

    # Get all unique years from the database
    cursor.execute("SELECT DISTINCT YEAR(playdate) AS year FROM rounds ORDER BY year DESC")
    unique_years = [row['year'] for row in cursor.fetchall()]

    # Get all unique golf courses from the database
    cursor.execute("SELECT DISTINCT gcname FROM rounds ORDER BY gcname ASC")
    unique_golf_courses = [row['gcname'] for row in cursor.fetchall()]

    # Get all unique companions from the database (assuming comma-separated)
    cursor.execute("SELECT DISTINCT coplayers FROM rounds")
    all_coplayers = []
    for row in cursor.fetchall():
        if row['coplayers']:
            all_coplayers.extend([c.strip() for c in row['coplayers'].split(',')])
    unique_companions = sorted(list(set(all_coplayers)))

    cursor.close() 
    conn.close()  

    return render_template('rounds.html', 
                           rounds=rounds, 
                           current_year=current_year,
                           selected_year=selected_year,
                           unique_years=unique_years,
                           selected_golf_course=selected_golf_course,
                           unique_golf_courses=unique_golf_courses,
                           selected_companion=selected_companion,
                           unique_companions=unique_companions,
                           sort_by=sort_by,
                           sort_order=sort_order,
                           search_query=search_query)

@app.route('/delete_round/<int:round_id>', methods=['POST'])
@login_required
def delete_round(round_id):
    db_config = current_app.config['DB_CONFIG']
    try:
        delete_round_data(round_id)
        flash('Round deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting round: {e}', 'danger')
    return redirect(url_for('list_rounds'))

@app.route('/round/<int:round_id>')
def round_detail(round_id):
    db_config = current_app.config['DB_CONFIG']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            r.*, 
            h.holenum, h.par, h.score as hole_score, h.putt,
            s.club, s.feelgrade, s.retgrade, s.concede, s.score as shot_score, s.penalty, s.retplace, s.shotplace, s.distance, s.error
        FROM rounds r
        LEFT JOIN holes h ON r.id = h.roundid
        LEFT JOIN shots s ON r.id = s.roundid AND h.holenum = s.holenum
        WHERE r.id = %s
        ORDER BY h.holenum, s.id
    """
    cursor.execute(query, (round_id,))
    results = cursor.fetchall()

    if not results:
        return "Round not found", 404

    round_info = {
        'id': results[0]['id'],
        'gcname': results[0]['gcname'],
        'player': results[0]['player'],
        'coplayers': results[0]['coplayers'],
        'playdate': results[0]['playdate'],
        'score': results[0]['score'],
        'gir': results[0]['gir'],
        'raw_data': results[0]['raw_data']
    }

    holes_info = [[], [], []]
    shots_by_hole = {}
    for row in results:
        if row['holenum'] not in shots_by_hole:
            shots_by_hole[row['holenum']] = []
            hole_data = {
                'holenum': row['holenum'],
                'par': row['par'],
                'score': row['hole_score'],
                'putt': row['putt'],
                'GIR': True if row['par'] >= row['hole_score'] - row['putt'] + 2 else False,
                'GIR1': True if row['par'] >= row['hole_score'] - row['putt'] + 1 else False,
                'diff': row['hole_score'] - row['par']
            }
            if row['holenum'] < 10:
                holes_info[0].append(hole_data)
            elif row['holenum'] < 19:
                holes_info[1].append(hole_data)
            else:
                holes_info[2].append(hole_data)
        
        shot_data = {
            'holenum': row['holenum'],
            'club': row['club'],
            'feel': row['feelgrade'],
            'result': row['retgrade'],
            'concede': row['concede'],
            'score': row['shot_score'],
            'penalty': row['penalty'],
            'retplace': row['retplace'],
            'on': row['shotplace'],
            'distance': row['distance'],
            'error': row['error']
        }
        if shot_data['error'] and shot_data['distance']:
            tmp = shot_data['error'] / shot_data['distance']
            shot_data['eresult'] = 'A' if tmp < 0.05 else 'B' if tmp < 0.1 else 'C'
        shots_by_hole[row['holenum']].append(shot_data)

    processed_shots = [shot for hole_shots in shots_by_hole.values() for shot in hole_shots]

    # Prepare data for club analysis chart
    club_counts = {}
    for shot in processed_shots:
        club = shot['club']
        if club in club_counts:
            club_counts[club] += 1
        else:
            club_counts[club] = 1
    
    club_labels = list(club_counts.keys())
    club_data = list(club_counts.values())

    # Analyze detailed shot statistics
    detailed_shot_stats = analyze_shots_and_stats(processed_shots)

    # Comparison data
    comparison_stats = {}

    # Overall average
    cursor.execute("""
        SELECT AVG(r.score) as avg_score, AVG(r.gir) as avg_gir, SUM(h.putt)/COUNT(DISTINCT r.id) as avg_putt
        FROM rounds r, holes h
        WHERE r.id = h.roundid
    """)
    comparison_stats['overall'] = cursor.fetchone()

    # Same golf course average
    cursor.execute("""
        SELECT AVG(r.score) as avg_score, AVG(r.gir) as avg_gir, SUM(h.putt)/COUNT(DISTINCT r.id) as avg_putt
        FROM rounds r, holes h
        WHERE r.id = h.roundid AND r.gcname = %s
    """, (round_info['gcname'],))
    comparison_stats['same_course'] = cursor.fetchone()

    # Recent 5 rounds average
    cursor.execute("""
        SELECT AVG(r.score) as avg_score, AVG(r.gir) as avg_gir, SUM(h.putt)/COUNT(DISTINCT r.id) as avg_putt
        FROM (
            SELECT id, score, gir, playdate FROM rounds ORDER BY playdate DESC LIMIT 5
        ) as r, holes h
        WHERE r.id = h.roundid
    """)
    comparison_stats['recent_5'] = cursor.fetchone()

    # Personal best
    cursor.execute("SELECT MIN(score) as best_score, MAX(gir) as best_gir FROM rounds")
    comparison_stats['personal_best'] = cursor.fetchone()

    # Previous and next rounds
    cursor.execute("(SELECT id, playdate, score FROM rounds WHERE playdate < %s ORDER BY playdate DESC LIMIT 1)", (round_info['playdate'],))
    comparison_stats['prev_round'] = cursor.fetchone()
    cursor.execute("(SELECT id, playdate, score FROM rounds WHERE playdate > %s ORDER BY playdate ASC LIMIT 1)", (round_info['playdate'],))
    comparison_stats['next_round'] = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('round_detail.html', 
                           round_info=round_info, 
                           holes_info=holes_info,
                           shots=processed_shots, # Still pass processed_shots for the detailed shots table
                           club_labels=club_labels, 
                           club_data=club_data, 
                           detailed_shot_stats=detailed_shot_stats,
                           comparison_stats=comparison_stats)

@app.route('/update_round_raw_data/<int:round_id>', methods=['POST'])
@login_required
def update_round_raw_data(round_id):
    raw_data_content = request.form['raw_data_content']
    
    # Save raw data to a temporary file for parse_file
    temp_file_path = "tmp/uploaded_golf_data.txt"
    with open(temp_file_path, 'w') as f:
        f.write(raw_data_content)

    try:
        parsed_data, scores_and_stats = parse_file(temp_file_path)
        parsed_data['id'] = round_id # Set the ID for update
        save_round_data(parsed_data, scores_and_stats, raw_data_content)
        flash('Raw data updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating raw data: {e}', 'danger')
    
    return redirect(url_for('round_detail', round_id=round_id))

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
            temp_file_path = "tmp/uploaded_golf_data.txt"
            with open(temp_file_path, 'w') as f:
                f.write(raw_data)
            
            try:
                parsed_data, scores_and_stats = parse_file(temp_file_path)
                session['parsed_data'] = parsed_data
                session['scores_and_stats'] = scores_and_stats
                session['raw_data_content'] = raw_data # Store raw content for saving to file later
                session['unparsed_lines'] = parsed_data.get('unparsed_lines', [])
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
    unparsed_lines = session.get('unparsed_lines')

    if not parsed_data or not scores_and_stats or not raw_data_content:
        return redirect(url_for('upload_round')) # Redirect if no data in session

    if request.method == 'POST':
        if request.form.get('action') == 'save':
            try:
                # Get potentially modified data from form
                raw_data_content = request.form['raw_data_content']
                parsed_data = json.loads(request.form['parsed_data'])
                scores_and_stats = json.loads(request.form['scores_and_stats'])

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
                save_round_data(parsed_data, scores_and_stats, raw_data_content)
                
                session.pop('parsed_data', None)
                session.pop('scores_and_stats', None)
                session.pop('raw_data_content', None)
                session.pop('unparsed_lines', None)
                
                return redirect(url_for('list_rounds')) # Redirect to list after saving
            except json.JSONDecodeError as e:
                return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats, raw_data_content=raw_data_content, error=f"JSON parsing error: {e}. Please check your JSON format.")
            except Exception as e:
                return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats, raw_data_content=raw_data_content, error=f"Save error: {e}")
        elif request.form.get('action') == 'reparse':
            raw_data_content = request.form['raw_data_content']
            temp_file_path = "tmp/uploaded_golf_data.txt"
            with open(temp_file_path, 'w') as f:
                f.write(raw_data_content)
            try:
                parsed_data, scores_and_stats = parse_file(temp_file_path)
                session['parsed_data'] = parsed_data
                session['scores_and_stats'] = scores_and_stats
                session['raw_data_content'] = raw_data_content
                session['unparsed_lines'] = parsed_data.get('unparsed_lines', [])
                flash('Data re-parsed successfully!', 'success')
            except Exception as e:
                flash(f'Error re-parsing data: {e}', 'danger')
                session['parsed_data'] = None # Clear parsed data on re-parse error
                session['scores_and_stats'] = None
                session['unparsed_lines'] = [raw_data_content] # Show the raw data as unparsed
            return redirect(url_for('review_round'))
        elif request.form.get('action') == 'cancel':
            session.pop('parsed_data', None)
            session.pop('scores_and_stats', None)
            session.pop('raw_data_content', None)
            session.pop('unparsed_lines', None)
            return redirect(url_for('upload_round'))

    parsed_data = session.get('parsed_data')
    scores_and_stats = session.get('scores_and_stats')
    raw_data_content = session.get('raw_data_content')
    unparsed_lines = session.get('unparsed_lines')

    return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats, raw_data_content=raw_data_content, unparsed_lines=unparsed_lines)
