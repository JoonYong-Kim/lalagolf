
from flask import render_template, current_app, jsonify, request, session, redirect, url_for, flash
from src.analytics_config import (
    APPROACH_STRATEGY_MIN_SAMPLES,
    CLUB_RELIABILITY_MIN_SAMPLES,
    EXPECTED_SCORE_MIN_SAMPLES,
    TEE_STRATEGY_MIN_SAMPLES,
)
from src.webapp import app
from src.db_loader import (
    delete_round_data,
    get_db_connection,
    get_filtered_rounds,
    get_rounds_for_trend_analysis,
    get_unique_companions,
    get_unique_golf_courses,
    get_unique_years,
    get_yearly_round_statistics,
    init_connection_pool,
    save_round_data,
)
from src.data_parser import parse_file, parse_content, analyze_shots_and_stats # Import analyze_shots_and_stats
from src.metrics import (
    build_birdie_follow_up_summary,
    build_closing_stretch_summary,
    build_course_adjustment_summary,
    build_momentum_follow_up_summary,
    build_nine_split_summary,
    build_penalty_recovery_summary,
    build_target_pressure_summary,
    build_round_metrics,
    build_recent_summary,
)
from src.shot_model import normalize_shot_states, build_shot_state_summary
from src.expected_value import build_expected_score_table, build_round_recency_weights
from src.recommendations import (
    build_recent_shot_value_window,
    build_recommendations,
    build_round_explanation_cards,
    build_round_hybrid_action_card,
    build_round_loss_cards,
    build_round_next_action_card,
    build_trend_action_cards,
)
from src.strokes_gained import (
    summarize_approach_strategy_comparison,
    build_historical_shot_facts,
    build_shot_values,
    summarize_club_reliability,
    summarize_tee_strategy_comparison,
    summarize_category_window,
    summarize_shot_values,
    summarize_shot_values_by_round,
)
from collections import defaultdict
import os
from datetime import datetime
from functools import wraps
import json
import numpy as np

def _parse_raw_round_data(raw_data: str, file_name: str = "<web>"):
    raw_content, parsed_data, scores_and_stats = parse_content(raw_data, file_name=file_name)
    if parsed_data.get('unparsed_lines'):
        raise ValueError(
            "Unparsed lines remain. Please correct the raw data and re-parse before saving."
        )
    return raw_content, parsed_data, scores_and_stats

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

def _parse_analysis_window(value, default='all'):
    if value is None:
        return default
    if value == 'all':
        return 'all'
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return str(parsed)

def _parse_round_ids(values):
    round_ids = []
    for value in values or []:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed <= 0 or parsed in round_ids:
            continue
        round_ids.append(parsed)
    return round_ids

def _resolve_window_size(selected_window, round_count):
    if selected_window == 'all':
        return round_count
    return min(int(selected_window), round_count) if round_count else int(selected_window)

def _build_analysis_scope(selected_year, selected_window, round_count, selected_golf_course='all', selected_companion='all', selected_round_ids=None):
    scope_parts = []
    selected_round_ids = selected_round_ids or []

    if selected_round_ids:
        scope_parts.append(f"선택 라운드 {len(selected_round_ids)}개")
    elif selected_year != 'all':
        scope_parts.append(f"{selected_year}년")
    else:
        scope_parts.append("전체 연도")

    if selected_golf_course != 'all':
        scope_parts.append(selected_golf_course)
    if selected_companion != 'all':
        scope_parts.append(f"동반자 {selected_companion}")

    if selected_window == 'all':
        window_label = "선택 범위 전체"
    else:
        window_label = f"최근 {selected_window}라운드"
    scope_parts.append(window_label)

    return {
        "label": " / ".join(scope_parts),
        "round_count": round_count,
        "selected_window": selected_window,
        "window_label": window_label,
        "is_filtered": bool(selected_round_ids) or any(value != 'all' for value in (selected_year, selected_golf_course, selected_companion)) or selected_window != 'all',
    }

def _build_analysis_context(selected_year='all', selected_window='all', selected_golf_course='all', selected_companion='all', selected_round_ids=None):
    selected_round_ids = selected_round_ids or []
    raw_trend_data = get_rounds_for_trend_analysis(
        year=selected_year,
        golf_course=selected_golf_course,
        companion=selected_companion,
        round_ids=selected_round_ids or None,
    )
    round_ids = {
        row["round_id"]
        for row in raw_trend_data
        if row.get("round_id") is not None
    }
    round_count = len(round_ids)
    window_size = _resolve_window_size(selected_window, round_count)
    recent_summary = build_recent_summary(raw_trend_data, window=window_size)
    historical_shot_facts = build_historical_shot_facts(raw_trend_data)
    round_weights = build_round_recency_weights(raw_trend_data)
    expected_score_table = build_expected_score_table(
        historical_shot_facts,
        round_weights=round_weights,
    ) if historical_shot_facts else {}
    valued_historical_shots = build_shot_values(
        historical_shot_facts,
        expected_score_table,
        min_samples=EXPECTED_SCORE_MIN_SAMPLES if len(historical_shot_facts) > 1 else 1,
    ) if historical_shot_facts else []
    shot_value_by_round = summarize_shot_values_by_round(valued_historical_shots) if valued_historical_shots else {}
    recent_shot_value_window = build_recent_shot_value_window(raw_trend_data, shot_value_by_round, window=window_size)
    recommendations = build_recommendations(recent_summary, recent_shot_value_window)
    trend_action_cards = build_trend_action_cards(recent_summary, recent_shot_value_window)

    return {
        "raw_trend_data": raw_trend_data,
        "round_count": round_count,
        "recent_summary": recent_summary,
        "recommendations": recommendations,
        "trend_action_cards": trend_action_cards,
        "analysis_scope": _build_analysis_scope(
            selected_year,
            selected_window,
            round_count,
            selected_golf_course=selected_golf_course,
            selected_companion=selected_companion,
            selected_round_ids=selected_round_ids,
        ),
    }

@app.route('/')
def home():
    selected_year = request.args.get('year', 'all')
    selected_window = _parse_analysis_window(request.args.get('analysis_window'), default='all')
    rounds = get_filtered_rounds(year=selected_year, sort_by='playdate', sort_order='ASC')
    labels = [r['playdate'].strftime('%Y-%m-%d') for r in rounds]
    data = [r['score'] for r in rounds]

    unique_years = get_unique_years()
    yearly_stats = get_yearly_round_statistics()
    analysis_context = _build_analysis_context(
        selected_year=selected_year,
        selected_window=selected_window,
    )

    return render_template('index.html', 
                           rounds=rounds, 
                           labels=labels, 
                           data=data, 
                           selected_year=selected_year,
                           selected_analysis_window=selected_window,
                           unique_years=unique_years,
                           yearly_stats=yearly_stats,
                           recent_summary=analysis_context['recent_summary'],
                           recommendations=analysis_context['recommendations'],
                           trend_action_cards=analysis_context['trend_action_cards'],
                           analysis_scope=analysis_context['analysis_scope'])

@app.route('/rounds')
def list_rounds():
    current_year = datetime.now().year
    selected_year = request.args.get('year', 'all')
    selected_golf_course = request.args.get('golf_course', 'all')
    selected_companion = request.args.get('companion', 'all')
    sort_by = request.args.get('sort_by', 'playdate')
    sort_order = request.args.get('sort_order', 'ASC')
    search_query = request.args.get('search_query')

    rounds = get_filtered_rounds(year=selected_year, golf_course=selected_golf_course, companion=selected_companion, sort_by=sort_by, sort_order=sort_order, search_query=search_query)
    unique_years = get_unique_years()
    unique_golf_courses = get_unique_golf_courses()
    unique_companions = get_unique_companions()

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

@app.route('/analysis')
def analysis_dashboard():
    selected_year = request.args.get('year', 'all')
    selected_golf_course = request.args.get('golf_course', 'all')
    selected_companion = request.args.get('companion', 'all')
    selected_window = _parse_analysis_window(request.args.get('analysis_window'), default='all')
    selected_round_ids = _parse_round_ids(request.args.getlist('round_ids'))
    sort_by = request.args.get('sort_by', 'playdate')
    sort_order = request.args.get('sort_order', 'ASC')
    search_query = request.args.get('search_query')

    rounds = get_filtered_rounds(
        year=selected_year,
        golf_course=selected_golf_course,
        companion=selected_companion,
        sort_by=sort_by,
        sort_order=sort_order,
        search_query=search_query,
    )
    unique_years = get_unique_years()
    unique_golf_courses = get_unique_golf_courses()
    unique_companions = get_unique_companions()
    analysis_context = _build_analysis_context(
        selected_year=selected_year,
        selected_window=selected_window,
        selected_golf_course=selected_golf_course,
        selected_companion=selected_companion,
        selected_round_ids=selected_round_ids,
    )

    return render_template(
        'analysis.html',
        rounds=rounds,
        selected_year=selected_year,
        selected_analysis_window=selected_window,
        unique_years=unique_years,
        selected_golf_course=selected_golf_course,
        unique_golf_courses=unique_golf_courses,
        selected_companion=selected_companion,
        unique_companions=unique_companions,
        sort_by=sort_by,
        sort_order=sort_order,
        search_query=search_query,
        selected_round_ids=selected_round_ids,
        recent_summary=analysis_context['recent_summary'],
        recommendations=analysis_context['recommendations'],
        trend_action_cards=analysis_context['trend_action_cards'],
        analysis_scope=analysis_context['analysis_scope'],
    )

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
    round_metrics = build_round_metrics(round_info, [hole for segment in holes_info for hole in segment], processed_shots)
    shot_facts = normalize_shot_states(round_info, [hole for segment in holes_info for hole in segment], processed_shots)
    raw_trend_data = get_rounds_for_trend_analysis()
    historical_shot_facts = build_historical_shot_facts(raw_trend_data)
    expected_score_table = build_expected_score_table(
        historical_shot_facts,
        round_weights=build_round_recency_weights(raw_trend_data),
    ) if historical_shot_facts else {}
    valued_historical_shots = build_shot_values(
        historical_shot_facts,
        expected_score_table,
        min_samples=EXPECTED_SCORE_MIN_SAMPLES if len(historical_shot_facts) > 1 else 1,
    ) if historical_shot_facts else []
    shot_facts = build_shot_values(
        shot_facts,
        expected_score_table,
        min_samples=EXPECTED_SCORE_MIN_SAMPLES if len(historical_shot_facts) > 1 else 1,
    )
    shot_state_summary = build_shot_state_summary(shot_facts)
    shot_value_summary = summarize_shot_values(shot_facts)

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
    recent_summary = build_recent_summary(raw_trend_data, window=10)
    shot_value_by_round = summarize_shot_values_by_round(valued_historical_shots) if valued_historical_shots else {}
    recent_shot_value_window = build_recent_shot_value_window(raw_trend_data, shot_value_by_round, window=10)
    round_explanation_cards = build_round_explanation_cards(round_metrics, comparison_stats)
    round_loss_cards = build_round_loss_cards(shot_value_summary)
    round_next_action_card = build_round_next_action_card(shot_value_summary, round_metrics)
    round_hybrid_action_card = build_round_hybrid_action_card(
        shot_value_summary,
        recent_summary,
        recent_shot_value_window,
        round_metrics,
    )

    cursor.close()
    conn.close()

    return render_template('round_detail.html', 
                           round_info=round_info, 
                           holes_info=holes_info,
                           shots=processed_shots, # Still pass processed_shots for the detailed shots table
                           club_labels=club_labels, 
                           club_data=club_data, 
                           detailed_shot_stats=detailed_shot_stats,
                           round_metrics=round_metrics,
                           shot_facts=shot_facts,
                           shot_state_summary=shot_state_summary,
                           shot_value_summary=shot_value_summary,
                           comparison_stats=comparison_stats,
                           round_explanation_cards=round_explanation_cards,
                           round_loss_cards=round_loss_cards,
                           round_next_action_card=round_next_action_card,
                           round_hybrid_action_card=round_hybrid_action_card)

@app.route('/update_round_raw_data/<int:round_id>', methods=['POST'])
@login_required
def update_round_raw_data(round_id):
    raw_data_content = request.form['raw_data_content']

    try:
        _, parsed_data, scores_and_stats = _parse_raw_round_data(raw_data_content, file_name=f"round:{round_id}")
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
            try:
                _, parsed_data, scores_and_stats = parse_content(raw_data, file_name="<upload>")
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
                raw_data_content = request.form['raw_data_content']
                _, parsed_data, scores_and_stats = _parse_raw_round_data(raw_data_content, file_name="<review>")

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
                save_round_data(parsed_data, scores_and_stats, raw_data_content)
                
                session.pop('parsed_data', None)
                session.pop('scores_and_stats', None)
                session.pop('raw_data_content', None)
                session.pop('unparsed_lines', None)
                
                return redirect(url_for('list_rounds')) # Redirect to list after saving
            except Exception as e:
                return render_template('review_data.html', parsed_data=parsed_data, scores_and_stats=scores_and_stats, raw_data_content=raw_data_content, error=f"Save error: {e}")
        elif request.form.get('action') == 'reparse':
            raw_data_content = request.form['raw_data_content']
            try:
                _, parsed_data, scores_and_stats = parse_content(raw_data_content, file_name="<review>")
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

@app.route('/trends')
def round_trends():
    raw_trend_data = get_all_rounds_for_trend_analysis()
    historical_shot_facts = build_historical_shot_facts(raw_trend_data)
    round_weights = build_round_recency_weights(raw_trend_data)
    expected_score_table = build_expected_score_table(historical_shot_facts, round_weights=round_weights) if historical_shot_facts else {}
    valued_historical_shots = build_shot_values(
        historical_shot_facts,
        expected_score_table,
        min_samples=EXPECTED_SCORE_MIN_SAMPLES if len(historical_shot_facts) > 1 else 1,
    ) if historical_shot_facts else []
    shot_value_by_round = summarize_shot_values_by_round(valued_historical_shots)
    
    # Group data by round_id
    rounds_data = defaultdict(lambda: {
        "id": None,
        "score": None,
        "gir": None,
        "gcname": None,
        "playdate": None,
        "total_putts_in_round": 0,
        "num_holes_in_round": 0,
        "ob_penalties": 0,
        "h_penalties": 0,
        "un_penalties": 0,
        "penalty_strokes": 0,
        "hole_pars": {},
        "hole_scores": {},
        "hole_putts": {},
        "shots_by_club_retgrade": defaultdict(lambda: {"A": 0, "B": 0, "C": 0}),
        "shots_per_hole": defaultdict(list),
        "par_type_scores": {3: [], 4: [], 5: []},
        "gir_hole_putts": [],
        "non_gir_hole_putts": [],
        "driver_tee_shots": 0,
        "driver_penalty_tee_shots": 0,
        "driver_result_c_tee_shots": 0,
        "under_160_holes": 0,
        "under_160_gir_holes": 0,
        "up_and_down_chances": 0,
        "up_and_down_success": 0,
        "shot_value_summary": None,
        "course_adjusted_score": None,
        "course_adjusted_to_par": None,
        "course_avg_score": None,
        "course_avg_score_to_par": None,
        "course_round_count": 0,
        "front_score": None,
        "back_score": None,
        "front_to_par": None,
        "back_to_par": None,
        "back_minus_front_to_par": None,
        "last_three_score": None,
        "last_three_to_par": None,
        "last_three_hole_count": 0,
        "closing_16_18_score": None,
        "closing_16_18_to_par": None,
        "closing_16_18_hole_count": 0,
        "birdie_follow_up_count": 0,
        "birdie_follow_up_to_par": None,
        "birdie_follow_up_par_save_rate": None,
        "penalty_recovery_count": 0,
        "penalty_recovery_to_par": None,
        "penalty_recovery_par_save_rate": None,
        "positive_momentum_count": 0,
        "positive_momentum_to_par": None,
        "positive_momentum_par_save_rate": None,
        "negative_momentum_count": 0,
        "negative_momentum_to_par": None,
        "negative_momentum_par_save_rate": None,
        "target_score": None,
        "target_hit": None,
        "target_closing_delta": None,
    }) # Added shots_by_club_retgrade
    for row in raw_trend_data:
        round_id = row['round_id']
        if rounds_data[round_id]["score"] is None:
            rounds_data[round_id]["id"] = round_id
            rounds_data[round_id]["score"] = row['round_score']
            rounds_data[round_id]["gir"] = row['round_gir']
            rounds_data[round_id]["gcname"] = row.get('gcname')
            rounds_data[round_id]["playdate"] = row['playdate']
            rounds_data[round_id]["shot_value_summary"] = shot_value_by_round.get(round_id)
        
        if row['putt'] is not None:
            rounds_data[round_id]["total_putts_in_round"] += row['putt']
            rounds_data[round_id]["num_holes_in_round"] += 1
        
        if row['penalty'] == 'OB':
            rounds_data[round_id]["ob_penalties"] += 1
            rounds_data[round_id]["penalty_strokes"] += 2
        elif row['penalty'] == 'H':
            rounds_data[round_id]["h_penalties"] += 1
            rounds_data[round_id]["penalty_strokes"] += 1
        elif row['penalty'] == 'UN':
            rounds_data[round_id]["un_penalties"] += 1
            rounds_data[round_id]["penalty_strokes"] += 1
        
        if row['holenum'] is not None and row['hole_par'] is not None and row['hole_score'] is not None:
            rounds_data[round_id]["hole_pars"][row['holenum']] = row['hole_par']
            rounds_data[round_id]["hole_scores"][row['holenum']] = row['hole_score']
            if row['hole_par'] in rounds_data[round_id]["par_type_scores"]:
                rounds_data[round_id]["par_type_scores"][row['hole_par']].append(row['hole_score'])
        if row['holenum'] is not None and row['putt'] is not None and row['holenum'] not in rounds_data[round_id]["hole_putts"]:
            rounds_data[round_id]["hole_putts"][row['holenum']] = row['putt']

        if row['holenum'] is not None and row['club'] is not None:
            rounds_data[round_id]["shots_per_hole"][row['holenum']].append({
                "club": row['club'],
                "penalty": row['penalty'],
                "result": row['retgrade'],
                "distance": row['distance'],
            })

        # Populate shots_by_club_retgrade
        club_type = None
        if row['club'] == 'D': club_type = 'Driver'
        elif row['club'] in ['W3', 'W5', 'UW', 'U3', 'U4']: club_type = 'Wood/Utility'
        elif row['club'] in ['I3', 'I4']: club_type = 'Long Iron'
        elif row['club'] in ['I5', 'I6', 'I7']: club_type = 'Middle Iron'
        elif row['club'] in ['I8', 'I9', 'IP', 'IA', '48']: club_type = 'Short Iron'
        elif row['club'] in ['52', '56', '58']: club_type = 'Wedge'
        elif row['club'] == 'P': club_type = 'Putter'

        if club_type and row['retgrade']:
            rounds_data[round_id]["shots_by_club_retgrade"][club_type][row['retgrade']] += 1

    course_adjustment_summary = build_course_adjustment_summary(raw_trend_data)
    nine_split_summary = build_nine_split_summary(raw_trend_data)
    closing_stretch_summary = build_closing_stretch_summary(raw_trend_data)
    birdie_follow_up_summary = build_birdie_follow_up_summary(raw_trend_data)
    penalty_recovery_summary = build_penalty_recovery_summary(raw_trend_data)
    momentum_follow_up_summary = build_momentum_follow_up_summary(raw_trend_data)
    target_pressure_summary = build_target_pressure_summary(raw_trend_data)

    # Calculate average putts per hole for each round and hole results
    for round_id, data in rounds_data.items():
        course_summary = course_adjustment_summary["rounds"].get(round_id, {})
        nine_summary = nine_split_summary.get(round_id, {})
        closing_summary = closing_stretch_summary.get(round_id, {})
        birdie_summary = birdie_follow_up_summary.get(round_id, {})
        penalty_summary = penalty_recovery_summary.get(round_id, {})
        momentum_summary = momentum_follow_up_summary.get(round_id, {})
        target_summary = target_pressure_summary.get(round_id, {})
        data["course_adjusted_score"] = course_summary.get("course_adjusted_score")
        data["course_adjusted_to_par"] = course_summary.get("course_adjusted_to_par")
        data["course_avg_score"] = course_summary.get("course_avg_score")
        data["course_avg_score_to_par"] = course_summary.get("course_avg_score_to_par")
        data["course_round_count"] = course_summary.get("course_round_count", 0)
        data["front_score"] = nine_summary.get("front_score")
        data["back_score"] = nine_summary.get("back_score")
        data["front_to_par"] = nine_summary.get("front_to_par")
        data["back_to_par"] = nine_summary.get("back_to_par")
        data["back_minus_front_to_par"] = nine_summary.get("back_minus_front_to_par")
        data["last_three_score"] = closing_summary.get("last_three_holes", {}).get("score")
        data["last_three_to_par"] = closing_summary.get("last_three_holes", {}).get("to_par")
        data["last_three_hole_count"] = closing_summary.get("last_three_holes", {}).get("hole_count", 0)
        data["closing_16_18_score"] = closing_summary.get("closing_16_18", {}).get("score")
        data["closing_16_18_to_par"] = closing_summary.get("closing_16_18", {}).get("to_par")
        data["closing_16_18_hole_count"] = closing_summary.get("closing_16_18", {}).get("hole_count", 0)
        data["birdie_follow_up_count"] = birdie_summary.get("follow_up_count", 0)
        data["birdie_follow_up_to_par"] = birdie_summary.get("avg_follow_up_to_par")
        data["birdie_follow_up_par_save_rate"] = birdie_summary.get("par_save_rate")
        data["penalty_recovery_count"] = penalty_summary.get("recovery_count", 0)
        data["penalty_recovery_to_par"] = penalty_summary.get("avg_recovery_to_par")
        data["penalty_recovery_par_save_rate"] = penalty_summary.get("par_save_rate")
        data["positive_momentum_count"] = momentum_summary.get("positive_count", 0)
        data["positive_momentum_to_par"] = momentum_summary.get("positive_avg_to_par")
        data["positive_momentum_par_save_rate"] = momentum_summary.get("positive_par_save_rate")
        data["negative_momentum_count"] = momentum_summary.get("negative_count", 0)
        data["negative_momentum_to_par"] = momentum_summary.get("negative_avg_to_par")
        data["negative_momentum_par_save_rate"] = momentum_summary.get("negative_par_save_rate")
        data["target_score"] = target_summary.get("target_score")
        data["target_hit"] = target_summary.get("target_hit")
        data["target_closing_delta"] = target_summary.get("closing_delta_to_target")
        rounds_data[round_id]["avg_putts_per_hole"] = data["total_putts_in_round"] / data["num_holes_in_round"] if data["num_holes_in_round"] > 0 else 0
        
        birdies = 0
        pars = 0
        bogeys = 0
        double_bogeys_plus = 0
        total_holes = 0
        one_putts = 0
        three_putts = 0
        scrambling_chances = 0
        scrambling_success = 0

        for holenum in data["hole_pars"]:
            hole_par = data["hole_pars"][holenum]
            hole_score = data["hole_scores"][holenum]
            diff = hole_score - hole_par
            if diff == -1:
                birdies += 1
            elif diff == 0:
                pars += 1
            elif diff == 1:
                bogeys += 1
            else:
                double_bogeys_plus += 1
            total_holes += 1

        tee_shot_penalty_holes = 0
        for holenum, shots in data["shots_per_hole"].items():
            putt = data["hole_putts"].get(holenum, 0)
            if putt == 1:
                one_putts += 1
            if putt >= 3:
                three_putts += 1

            hole_par = data["hole_pars"].get(holenum)
            hole_score = data["hole_scores"].get(holenum)
            if hole_par is not None and hole_score is not None:
                gir = hole_par >= hole_score - putt + 2
                if gir:
                    data["gir_hole_putts"].append(putt)
                else:
                    data["non_gir_hole_putts"].append(putt)
                    scrambling_chances += 1
                    if hole_score <= hole_par:
                        scrambling_success += 1

            under_160_hole = False
            up_and_down_hole = False
            if shots:
                if shots[0].get("penalty"):
                    tee_shot_penalty_holes += 1
                if shots[0].get("club") == "D":
                    data["driver_tee_shots"] += 1
                    if shots[0].get("penalty"):
                        data["driver_penalty_tee_shots"] += 1
                    if shots[0].get("result") == "C":
                        data["driver_result_c_tee_shots"] += 1
            for shot in shots:
                if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] < 160:
                    under_160_hole = True
                if shot.get("club") != "P" and shot.get("distance") is not None and shot["distance"] <= 30:
                    up_and_down_hole = True
            if under_160_hole:
                data["under_160_holes"] += 1
                if hole_par is not None and hole_score is not None and hole_par >= hole_score - putt + 2:
                    data["under_160_gir_holes"] += 1
            if hole_par is not None and hole_score is not None and not (hole_par >= hole_score - putt + 2) and up_and_down_hole:
                data["up_and_down_chances"] += 1
                if hole_score <= hole_par:
                    data["up_and_down_success"] += 1
        
        rounds_data[round_id]["birdies"] = birdies
        rounds_data[round_id]["pars"] = pars
        rounds_data[round_id]["bogeys"] = bogeys
        rounds_data[round_id]["double_bogeys_plus"] = double_bogeys_plus
        rounds_data[round_id]["total_holes"] = total_holes
        rounds_data[round_id]["one_putt_rate"] = one_putts / total_holes if total_holes > 0 else 0
        rounds_data[round_id]["three_putt_rate"] = three_putts / total_holes if total_holes > 0 else 0
        rounds_data[round_id]["scrambling_rate"] = scrambling_success / scrambling_chances if scrambling_chances > 0 else 0
        rounds_data[round_id]["up_and_down_rate"] = data["up_and_down_success"] / data["up_and_down_chances"] if data["up_and_down_chances"] > 0 else 0
        rounds_data[round_id]["tee_shot_penalty_rate"] = tee_shot_penalty_holes / total_holes if total_holes > 0 else 0
        rounds_data[round_id]["driver_penalty_rate"] = data["driver_penalty_tee_shots"] / data["driver_tee_shots"] if data["driver_tee_shots"] > 0 else 0
        rounds_data[round_id]["driver_result_c_rate"] = data["driver_result_c_tee_shots"] / data["driver_tee_shots"] if data["driver_tee_shots"] > 0 else 0
        rounds_data[round_id]["gir_from_under_160_rate"] = data["under_160_gir_holes"] / data["under_160_holes"] if data["under_160_holes"] > 0 else 0
        rounds_data[round_id]["score_to_par"] = sum(data["hole_scores"][h] - data["hole_pars"][h] for h in data["hole_pars"])
        rounds_data[round_id]["par3_score_to_par"] = sum(score - 3 for score in data["par_type_scores"][3]) if data["par_type_scores"][3] else 0
        rounds_data[round_id]["par4_score_to_par"] = sum(score - 4 for score in data["par_type_scores"][4]) if data["par_type_scores"][4] else 0
        rounds_data[round_id]["par5_score_to_par"] = sum(score - 5 for score in data["par_type_scores"][5]) if data["par_type_scores"][5] else 0

    # Define score ranges
    score_ranges = {
        "70s": (70, 79),
        "80-83": (80, 83),
        "84-86": (84, 86),
        "87-89": (87, 89),
        "90-93": (90, 93),
        "94+": (94, 200) # Assuming max score is 200 for practical purposes
    }

    # Define a fixed order for club types
    CLUB_ORDER = ['Driver', 'Wood/Utility', 'Long Iron', 'Middle Iron', 'Short Iron', 'Wedge', 'Putter']

    def init_trend_bucket():
        return {
            "scores": [],
            "score_to_par": [],
            "course_adjusted_to_par": [],
            "front_to_par": [],
            "back_to_par": [],
            "back_minus_front_to_par": [],
            "last_three_to_par": [],
            "closing_16_18_to_par": [],
            "birdie_follow_up_to_par": [],
            "birdie_follow_up_par_save_rate": [],
            "birdie_follow_up_count": 0,
            "penalty_recovery_to_par": [],
            "penalty_recovery_par_save_rate": [],
            "penalty_recovery_count": 0,
            "positive_momentum_to_par": [],
            "positive_momentum_par_save_rate": [],
            "positive_momentum_count": 0,
            "negative_momentum_to_par": [],
            "negative_momentum_par_save_rate": [],
            "negative_momentum_count": 0,
            "target_closing_delta": [],
            "target_hit_count": 0,
            "target_pressure_count": 0,
            "girs": [],
            "putts_per_hole_list": [],
            "ob_penalties": [],
            "h_penalties": [],
            "penalty_strokes": [],
            "one_putt_rates": [],
            "three_putt_rates": [],
            "scrambling_rates": [],
            "up_and_down_rates": [],
            "tee_shot_penalty_rates": [],
            "driver_penalty_rates": [],
            "driver_result_c_rates": [],
            "gir_from_under_160_rates": [],
            "par3_to_par": [],
            "par4_to_par": [],
            "par5_to_par": [],
            "birdies": 0,
            "pars": 0,
            "bogeys": 0,
            "double_bogeys_plus": 0,
            "total_holes": 0,
            "round_ids": set(),
            "shot_value_summaries": [],
        }

    calculated_trends = defaultdict(init_trend_bucket) # Use a set to count unique rounds
    club_trends_raw_counts = defaultdict(lambda: defaultdict(lambda: {"A": 0, "B": 0, "C": 0})) # Accumulate raw counts for A, B, C per club per score range
    recent_window_labels = ["Recent 5", "Recent 10", "Recent 20"]

    for round_id, data in rounds_data.items():
        score = data["score"]
        if score is None:
            continue

        for range_name, (min_score, max_score) in score_ranges.items():
            if min_score <= score <= max_score:
                # General Trends
                calculated_trends[range_name]["round_ids"].add(round_id) # Add unique round_id

                calculated_trends[range_name]["scores"].append(score)
                calculated_trends[range_name]["score_to_par"].append(data["score_to_par"])
                if data["course_adjusted_to_par"] is not None:
                    calculated_trends[range_name]["course_adjusted_to_par"].append(data["course_adjusted_to_par"])
                if data["front_to_par"] is not None:
                    calculated_trends[range_name]["front_to_par"].append(data["front_to_par"])
                if data["back_to_par"] is not None:
                    calculated_trends[range_name]["back_to_par"].append(data["back_to_par"])
                if data["back_minus_front_to_par"] is not None:
                    calculated_trends[range_name]["back_minus_front_to_par"].append(data["back_minus_front_to_par"])
                if data["last_three_to_par"] is not None:
                    calculated_trends[range_name]["last_three_to_par"].append(data["last_three_to_par"])
                if data["closing_16_18_to_par"] is not None:
                    calculated_trends[range_name]["closing_16_18_to_par"].append(data["closing_16_18_to_par"])
                if data["birdie_follow_up_to_par"] is not None:
                    calculated_trends[range_name]["birdie_follow_up_to_par"].append(data["birdie_follow_up_to_par"])
                if data["birdie_follow_up_par_save_rate"] is not None:
                    calculated_trends[range_name]["birdie_follow_up_par_save_rate"].append(data["birdie_follow_up_par_save_rate"])
                if data["penalty_recovery_to_par"] is not None:
                    calculated_trends[range_name]["penalty_recovery_to_par"].append(data["penalty_recovery_to_par"])
                if data["penalty_recovery_par_save_rate"] is not None:
                    calculated_trends[range_name]["penalty_recovery_par_save_rate"].append(data["penalty_recovery_par_save_rate"])
                if data["positive_momentum_to_par"] is not None:
                    calculated_trends[range_name]["positive_momentum_to_par"].append(data["positive_momentum_to_par"])
                if data["positive_momentum_par_save_rate"] is not None:
                    calculated_trends[range_name]["positive_momentum_par_save_rate"].append(data["positive_momentum_par_save_rate"])
                if data["negative_momentum_to_par"] is not None:
                    calculated_trends[range_name]["negative_momentum_to_par"].append(data["negative_momentum_to_par"])
                if data["negative_momentum_par_save_rate"] is not None:
                    calculated_trends[range_name]["negative_momentum_par_save_rate"].append(data["negative_momentum_par_save_rate"])
                if data["target_closing_delta"] is not None:
                    calculated_trends[range_name]["target_closing_delta"].append(data["target_closing_delta"])
                if data["gir"] is not None:
                    calculated_trends[range_name]["girs"].append(data["gir"])
                if data["avg_putts_per_hole"] is not None:
                    calculated_trends[range_name]["putts_per_hole_list"].append(data["avg_putts_per_hole"])
                calculated_trends[range_name]["ob_penalties"].append(data["ob_penalties"])
                calculated_trends[range_name]["h_penalties"].append(data["h_penalties"])
                calculated_trends[range_name]["penalty_strokes"].append(data["penalty_strokes"])
                calculated_trends[range_name]["one_putt_rates"].append(data["one_putt_rate"])
                calculated_trends[range_name]["three_putt_rates"].append(data["three_putt_rate"])
                calculated_trends[range_name]["scrambling_rates"].append(data["scrambling_rate"])
                calculated_trends[range_name]["up_and_down_rates"].append(data["up_and_down_rate"])
                calculated_trends[range_name]["tee_shot_penalty_rates"].append(data["tee_shot_penalty_rate"])
                calculated_trends[range_name]["driver_penalty_rates"].append(data["driver_penalty_rate"])
                calculated_trends[range_name]["driver_result_c_rates"].append(data["driver_result_c_rate"])
                calculated_trends[range_name]["gir_from_under_160_rates"].append(data["gir_from_under_160_rate"])
                calculated_trends[range_name]["par3_to_par"].append(data["par3_score_to_par"])
                calculated_trends[range_name]["par4_to_par"].append(data["par4_score_to_par"])
                calculated_trends[range_name]["par5_to_par"].append(data["par5_score_to_par"])
                if data["shot_value_summary"]:
                    calculated_trends[range_name]["shot_value_summaries"].append(data["shot_value_summary"])

                calculated_trends[range_name]["birdies"] += data["birdies"]
                calculated_trends[range_name]["birdie_follow_up_count"] += data["birdie_follow_up_count"]
                calculated_trends[range_name]["penalty_recovery_count"] += data["penalty_recovery_count"]
                calculated_trends[range_name]["positive_momentum_count"] += data["positive_momentum_count"]
                calculated_trends[range_name]["negative_momentum_count"] += data["negative_momentum_count"]
                if data["target_score"] is not None:
                    calculated_trends[range_name]["target_pressure_count"] += 1
                    if data["target_hit"]:
                        calculated_trends[range_name]["target_hit_count"] += 1
                calculated_trends[range_name]["pars"] += data["pars"]
                calculated_trends[range_name]["bogeys"] += data["bogeys"]
                calculated_trends[range_name]["double_bogeys_plus"] += data["double_bogeys_plus"]
                calculated_trends[range_name]["total_holes"] += data["total_holes"]

                # Club Trends - accumulate raw counts for A, B, C per club per score range
                for club_type, grades in data["shots_by_club_retgrade"].items():
                    club_trends_raw_counts[range_name][club_type]["A"] += grades["A"]
                    club_trends_raw_counts[range_name][club_type]["B"] += grades["B"]
                    club_trends_raw_counts[range_name][club_type]["C"] += grades["C"]

                break # Found the range, move to next round

    final_trends = {}
    final_club_trends = {}

    for range_name in score_ranges.keys():
        stats = calculated_trends[range_name]
        num_rounds_in_range = len(stats["round_ids"]) # Corrected round count
        shot_value_window = summarize_category_window(stats["shot_value_summaries"])

        final_trends[range_name] = {
            "round_count": num_rounds_in_range,
            "avg_score": sum(stats["scores"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_score_to_par": sum(stats["score_to_par"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_course_adjusted_to_par": (
                sum(stats["course_adjusted_to_par"]) / len(stats["course_adjusted_to_par"])
                if stats["course_adjusted_to_par"] else None
            ),
            "avg_front_to_par": (
                sum(stats["front_to_par"]) / len(stats["front_to_par"])
                if stats["front_to_par"] else None
            ),
            "avg_back_to_par": (
                sum(stats["back_to_par"]) / len(stats["back_to_par"])
                if stats["back_to_par"] else None
            ),
            "avg_back_minus_front_to_par": (
                sum(stats["back_minus_front_to_par"]) / len(stats["back_minus_front_to_par"])
                if stats["back_minus_front_to_par"] else None
            ),
            "avg_last_three_to_par": (
                sum(stats["last_three_to_par"]) / len(stats["last_three_to_par"])
                if stats["last_three_to_par"] else None
            ),
            "avg_closing_16_18_to_par": (
                sum(stats["closing_16_18_to_par"]) / len(stats["closing_16_18_to_par"])
                if stats["closing_16_18_to_par"] else None
            ),
            "birdie_follow_up_count": stats["birdie_follow_up_count"],
            "avg_birdie_follow_up_to_par": (
                sum(stats["birdie_follow_up_to_par"]) / len(stats["birdie_follow_up_to_par"])
                if stats["birdie_follow_up_to_par"] else None
            ),
            "birdie_follow_up_par_save_rate": (
                sum(stats["birdie_follow_up_par_save_rate"]) / len(stats["birdie_follow_up_par_save_rate"])
                if stats["birdie_follow_up_par_save_rate"] else None
            ),
            "penalty_recovery_count": stats["penalty_recovery_count"],
            "avg_penalty_recovery_to_par": (
                sum(stats["penalty_recovery_to_par"]) / len(stats["penalty_recovery_to_par"])
                if stats["penalty_recovery_to_par"] else None
            ),
            "penalty_recovery_par_save_rate": (
                sum(stats["penalty_recovery_par_save_rate"]) / len(stats["penalty_recovery_par_save_rate"])
                if stats["penalty_recovery_par_save_rate"] else None
            ),
            "positive_momentum_count": stats["positive_momentum_count"],
            "avg_positive_momentum_to_par": (
                sum(stats["positive_momentum_to_par"]) / len(stats["positive_momentum_to_par"])
                if stats["positive_momentum_to_par"] else None
            ),
            "positive_momentum_par_save_rate": (
                sum(stats["positive_momentum_par_save_rate"]) / len(stats["positive_momentum_par_save_rate"])
                if stats["positive_momentum_par_save_rate"] else None
            ),
            "negative_momentum_count": stats["negative_momentum_count"],
            "avg_negative_momentum_to_par": (
                sum(stats["negative_momentum_to_par"]) / len(stats["negative_momentum_to_par"])
                if stats["negative_momentum_to_par"] else None
            ),
            "negative_momentum_par_save_rate": (
                sum(stats["negative_momentum_par_save_rate"]) / len(stats["negative_momentum_par_save_rate"])
                if stats["negative_momentum_par_save_rate"] else None
            ),
            "target_pressure_count": stats["target_pressure_count"],
            "target_hit_rate": (
                stats["target_hit_count"] / stats["target_pressure_count"]
                if stats["target_pressure_count"] else None
            ),
            "avg_target_closing_delta": (
                sum(stats["target_closing_delta"]) / len(stats["target_closing_delta"])
                if stats["target_closing_delta"] else None
            ),
            "min_gir": min(stats["girs"]) if stats["girs"] else None,
            "max_gir": max(stats["girs"]) if stats["girs"] else None,
            "avg_gir": sum(stats["girs"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "min_putts": min(stats["putts_per_hole_list"]) if stats["putts_per_hole_list"] else None,
            "max_putts": max(stats["putts_per_hole_list"]) if stats["putts_per_hole_list"] else None,
            "avg_putts": sum(stats["putts_per_hole_list"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_ob_penalties": sum(stats["ob_penalties"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_h_penalties": sum(stats["h_penalties"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_penalty_strokes": sum(stats["penalty_strokes"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_one_putt_rate": sum(stats["one_putt_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_three_putt_rate": sum(stats["three_putt_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_scrambling_rate": sum(stats["scrambling_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_up_and_down_rate": sum(stats["up_and_down_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_tee_shot_penalty_rate": sum(stats["tee_shot_penalty_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_driver_penalty_rate": sum(stats["driver_penalty_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_driver_result_c_rate": sum(stats["driver_result_c_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_gir_from_under_160_rate": sum(stats["gir_from_under_160_rates"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_par3_to_par": sum(stats["par3_to_par"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_par4_to_par": sum(stats["par4_to_par"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "avg_par5_to_par": sum(stats["par5_to_par"]) / num_rounds_in_range if num_rounds_in_range > 0 else None,
            "birdie_ratio": stats["birdies"] / stats["total_holes"] if stats["total_holes"] > 0 else None,
            "par_ratio": stats["pars"] / stats["total_holes"] if stats["total_holes"] > 0 else None,
            "bogey_ratio": stats["bogeys"] / stats["total_holes"] if stats["total_holes"] > 0 else None,
            "double_bogey_plus_ratio": stats["double_bogeys_plus"] / stats["total_holes"] if stats["total_holes"] > 0 else None,
            "shot_value_summary": shot_value_window,
        }

        # Calculate club average shots per round for A, B, C
        final_club_trends[range_name] = {}
        for club_type in CLUB_ORDER: # Iterate through fixed order
            grades = club_trends_raw_counts[range_name][club_type]
            final_club_trends[range_name][club_type] = {
                "A": grades["A"] / num_rounds_in_range if num_rounds_in_range > 0 else 0,
                "B": grades["B"] / num_rounds_in_range if num_rounds_in_range > 0 else 0,
                "C": grades["C"] / num_rounds_in_range if num_rounds_in_range > 0 else 0,
            }
            # Ensure all club types are present even if no data for a range
            if club_type not in club_trends_raw_counts[range_name]:
                 final_club_trends[range_name][club_type] = {"A": 0, "B": 0, "C": 0}

    sorted_rounds = sorted(
        [data for data in rounds_data.values() if data["score"] is not None and data["playdate"] is not None],
        key=lambda item: item["playdate"],
        reverse=True,
    )
    recent_trends = {}
    recent_shot_value_trends = {}
    for label in recent_window_labels:
        window_size = int(label.split()[1])
        selected = sorted_rounds[:window_size]
        round_count = len(selected)
        total_holes = sum(item["total_holes"] for item in selected)
        birdies = sum(item["birdies"] for item in selected)
        pars = sum(item["pars"] for item in selected)
        bogeys = sum(item["bogeys"] for item in selected)
        double_plus = sum(item["double_bogeys_plus"] for item in selected)
        selected_course_adjusted = [item["course_adjusted_to_par"] for item in selected if item["course_adjusted_to_par"] is not None]
        selected_front_to_par = [item["front_to_par"] for item in selected if item["front_to_par"] is not None]
        selected_back_to_par = [item["back_to_par"] for item in selected if item["back_to_par"] is not None]
        selected_back_minus_front = [item["back_minus_front_to_par"] for item in selected if item["back_minus_front_to_par"] is not None]
        selected_last_three_to_par = [item["last_three_to_par"] for item in selected if item["last_three_to_par"] is not None]
        selected_closing_16_18_to_par = [item["closing_16_18_to_par"] for item in selected if item["closing_16_18_to_par"] is not None]
        selected_birdie_follow_up_to_par = [item["birdie_follow_up_to_par"] for item in selected if item["birdie_follow_up_to_par"] is not None]
        selected_birdie_follow_up_par_save_rate = [item["birdie_follow_up_par_save_rate"] for item in selected if item["birdie_follow_up_par_save_rate"] is not None]
        selected_penalty_recovery_to_par = [item["penalty_recovery_to_par"] for item in selected if item["penalty_recovery_to_par"] is not None]
        selected_penalty_recovery_par_save_rate = [item["penalty_recovery_par_save_rate"] for item in selected if item["penalty_recovery_par_save_rate"] is not None]
        selected_positive_momentum_to_par = [item["positive_momentum_to_par"] for item in selected if item["positive_momentum_to_par"] is not None]
        selected_positive_momentum_par_save_rate = [item["positive_momentum_par_save_rate"] for item in selected if item["positive_momentum_par_save_rate"] is not None]
        selected_negative_momentum_to_par = [item["negative_momentum_to_par"] for item in selected if item["negative_momentum_to_par"] is not None]
        selected_negative_momentum_par_save_rate = [item["negative_momentum_par_save_rate"] for item in selected if item["negative_momentum_par_save_rate"] is not None]
        selected_target_closing_delta = [item["target_closing_delta"] for item in selected if item["target_closing_delta"] is not None]
        recent_trends[label] = {
            "round_count": round_count,
            "avg_score": sum(item["score"] for item in selected) / round_count if round_count else None,
            "avg_score_to_par": sum(item["score_to_par"] for item in selected) / round_count if round_count else None,
            "avg_course_adjusted_to_par": (
                sum(selected_course_adjusted) / len(selected_course_adjusted)
                if selected_course_adjusted else None
            ),
            "avg_front_to_par": (
                sum(selected_front_to_par) / len(selected_front_to_par)
                if selected_front_to_par else None
            ),
            "avg_back_to_par": (
                sum(selected_back_to_par) / len(selected_back_to_par)
                if selected_back_to_par else None
            ),
            "avg_back_minus_front_to_par": (
                sum(selected_back_minus_front) / len(selected_back_minus_front)
                if selected_back_minus_front else None
            ),
            "avg_last_three_to_par": (
                sum(selected_last_three_to_par) / len(selected_last_three_to_par)
                if selected_last_three_to_par else None
            ),
            "avg_closing_16_18_to_par": (
                sum(selected_closing_16_18_to_par) / len(selected_closing_16_18_to_par)
                if selected_closing_16_18_to_par else None
            ),
            "birdie_follow_up_count": sum(item["birdie_follow_up_count"] for item in selected),
            "avg_birdie_follow_up_to_par": (
                sum(selected_birdie_follow_up_to_par) / len(selected_birdie_follow_up_to_par)
                if selected_birdie_follow_up_to_par else None
            ),
            "birdie_follow_up_par_save_rate": (
                sum(selected_birdie_follow_up_par_save_rate) / len(selected_birdie_follow_up_par_save_rate)
                if selected_birdie_follow_up_par_save_rate else None
            ),
            "penalty_recovery_count": sum(item["penalty_recovery_count"] for item in selected),
            "avg_penalty_recovery_to_par": (
                sum(selected_penalty_recovery_to_par) / len(selected_penalty_recovery_to_par)
                if selected_penalty_recovery_to_par else None
            ),
            "penalty_recovery_par_save_rate": (
                sum(selected_penalty_recovery_par_save_rate) / len(selected_penalty_recovery_par_save_rate)
                if selected_penalty_recovery_par_save_rate else None
            ),
            "positive_momentum_count": sum(item["positive_momentum_count"] for item in selected),
            "avg_positive_momentum_to_par": (
                sum(selected_positive_momentum_to_par) / len(selected_positive_momentum_to_par)
                if selected_positive_momentum_to_par else None
            ),
            "positive_momentum_par_save_rate": (
                sum(selected_positive_momentum_par_save_rate) / len(selected_positive_momentum_par_save_rate)
                if selected_positive_momentum_par_save_rate else None
            ),
            "negative_momentum_count": sum(item["negative_momentum_count"] for item in selected),
            "avg_negative_momentum_to_par": (
                sum(selected_negative_momentum_to_par) / len(selected_negative_momentum_to_par)
                if selected_negative_momentum_to_par else None
            ),
            "negative_momentum_par_save_rate": (
                sum(selected_negative_momentum_par_save_rate) / len(selected_negative_momentum_par_save_rate)
                if selected_negative_momentum_par_save_rate else None
            ),
            "target_pressure_count": sum(1 for item in selected if item["target_score"] is not None),
            "target_hit_rate": (
                sum(1 for item in selected if item["target_hit"]) /
                sum(1 for item in selected if item["target_score"] is not None)
                if any(item["target_score"] is not None for item in selected) else None
            ),
            "avg_target_closing_delta": (
                sum(selected_target_closing_delta) / len(selected_target_closing_delta)
                if selected_target_closing_delta else None
            ),
            "avg_gir": sum(item["gir"] for item in selected) / round_count if round_count else None,
            "avg_putts": sum(item["avg_putts_per_hole"] for item in selected) / round_count if round_count else None,
            "avg_one_putt_rate": sum(item["one_putt_rate"] for item in selected) / round_count if round_count else None,
            "avg_three_putt_rate": sum(item["three_putt_rate"] for item in selected) / round_count if round_count else None,
            "avg_scrambling_rate": sum(item["scrambling_rate"] for item in selected) / round_count if round_count else None,
            "avg_up_and_down_rate": sum(item["up_and_down_rate"] for item in selected) / round_count if round_count else None,
            "avg_penalty_strokes": sum(item["penalty_strokes"] for item in selected) / round_count if round_count else None,
            "avg_tee_shot_penalty_rate": sum(item["tee_shot_penalty_rate"] for item in selected) / round_count if round_count else None,
            "avg_driver_penalty_rate": sum(item["driver_penalty_rate"] for item in selected) / round_count if round_count else None,
            "avg_driver_result_c_rate": sum(item["driver_result_c_rate"] for item in selected) / round_count if round_count else None,
            "avg_gir_from_under_160_rate": sum(item["gir_from_under_160_rate"] for item in selected) / round_count if round_count else None,
            "avg_par3_to_par": sum(item["par3_score_to_par"] for item in selected) / round_count if round_count else None,
            "avg_par4_to_par": sum(item["par4_score_to_par"] for item in selected) / round_count if round_count else None,
            "avg_par5_to_par": sum(item["par5_score_to_par"] for item in selected) / round_count if round_count else None,
            "birdie_ratio": birdies / total_holes if total_holes else None,
            "par_ratio": pars / total_holes if total_holes else None,
            "bogey_ratio": bogeys / total_holes if total_holes else None,
            "double_bogey_plus_ratio": double_plus / total_holes if total_holes else None,
        }
        recent_shot_value_trends[label] = summarize_category_window(
            [item["shot_value_summary"] for item in selected if item.get("shot_value_summary")]
        )

    recent_shot_value_window = build_recent_shot_value_window(raw_trend_data, shot_value_by_round, window=10)
    recent_summary = build_recent_summary(raw_trend_data, window=10)
    recommendations = build_recommendations(recent_summary, recent_shot_value_window)
    trend_action_cards = build_trend_action_cards(recent_summary, recent_shot_value_window)
    recent_round_ids = {item["id"] for item in sorted_rounds[:10] if item.get("id") is not None}
    recent_valued_shots = [fact for fact in valued_historical_shots if fact.get("round_id") in recent_round_ids]
    club_reliability_report = summarize_club_reliability(
        recent_valued_shots,
        min_samples=CLUB_RELIABILITY_MIN_SAMPLES,
    )
    tee_strategy_comparison = summarize_tee_strategy_comparison(
        recent_valued_shots,
        min_samples=TEE_STRATEGY_MIN_SAMPLES,
    )
    approach_strategy_comparison = summarize_approach_strategy_comparison(
        recent_valued_shots,
        min_samples=APPROACH_STRATEGY_MIN_SAMPLES,
    )

    # Calculate correlations
    scores = [d['score'] for d in rounds_data.values() if d['score'] is not None]
    girs = [d['gir'] for d in rounds_data.values() if d['score'] is not None]
    avg_putts = [d['avg_putts_per_hole'] for d in rounds_data.values() if d['score'] is not None]
    ob_penalties = [d['ob_penalties'] for d in rounds_data.values() if d['score'] is not None]
    h_penalties = [d['h_penalties'] for d in rounds_data.values() if d['score'] is not None]
    penalty_strokes = [d['penalty_strokes'] for d in rounds_data.values() if d['score'] is not None]
    three_putt_rates = [d['three_putt_rate'] for d in rounds_data.values() if d['score'] is not None]
    scrambling_rates = [d['scrambling_rate'] for d in rounds_data.values() if d['score'] is not None]
    up_and_down_rates = [d['up_and_down_rate'] for d in rounds_data.values() if d['score'] is not None]
    tee_shot_penalty_rates = [d['tee_shot_penalty_rate'] for d in rounds_data.values() if d['score'] is not None]
    driver_penalty_rates = [d['driver_penalty_rate'] for d in rounds_data.values() if d['score'] is not None]
    driver_result_c_rates = [d['driver_result_c_rate'] for d in rounds_data.values() if d['score'] is not None]
    gir_from_under_160_rates = [d['gir_from_under_160_rate'] for d in rounds_data.values() if d['score'] is not None]
    birdie_ratios = [d['birdies'] / d['total_holes'] if d['total_holes'] > 0 else 0 for d in rounds_data.values() if d['score'] is not None]
    par_ratios = [d['pars'] / d['total_holes'] if d['total_holes'] > 0 else 0 for d in rounds_data.values() if d['score'] is not None]
    bogey_ratios = [d['bogeys'] / d['total_holes'] if d['total_holes'] > 0 else 0 for d in rounds_data.values() if d['score'] is not None]
    double_bogey_plus_ratios = [d['double_bogeys_plus'] / d['total_holes'] if d['total_holes'] > 0 else 0 for d in rounds_data.values() if d['score'] is not None]

    correlation_data = {}
    if len(scores) > 1:
        correlation_data['GIR'] = np.corrcoef(scores, girs)[0, 1]
        correlation_data['Avg Putts'] = np.corrcoef(scores, avg_putts)[0, 1]
        correlation_data['OB Penalties'] = np.corrcoef(scores, ob_penalties)[0, 1]
        correlation_data['H Penalties'] = np.corrcoef(scores, h_penalties)[0, 1]
        correlation_data['Penalty Strokes'] = np.corrcoef(scores, penalty_strokes)[0, 1]
        correlation_data['3-Putt Rate'] = np.corrcoef(scores, three_putt_rates)[0, 1]
        correlation_data['Scrambling'] = np.corrcoef(scores, scrambling_rates)[0, 1]
        correlation_data['Up-and-Down'] = np.corrcoef(scores, up_and_down_rates)[0, 1]
        correlation_data['Tee Shot Penalty Rate'] = np.corrcoef(scores, tee_shot_penalty_rates)[0, 1]
        correlation_data['Driver Penalty Rate'] = np.corrcoef(scores, driver_penalty_rates)[0, 1]
        correlation_data['Driver Result C Rate'] = np.corrcoef(scores, driver_result_c_rates)[0, 1]
        correlation_data['GIR from <160m'] = np.corrcoef(scores, gir_from_under_160_rates)[0, 1]
        correlation_data['Birdie Ratio'] = np.corrcoef(scores, birdie_ratios)[0, 1]
        correlation_data['Par Ratio'] = np.corrcoef(scores, par_ratios)[0, 1]
        correlation_data['Bogey Ratio'] = np.corrcoef(scores, bogey_ratios)[0, 1]
        correlation_data['Double Bogey+ Ratio'] = np.corrcoef(scores, double_bogey_plus_ratios)[0, 1]

    return render_template(
        'round_trends.html',
        calculated_trends=final_trends,
        recent_trends=recent_trends,
        recent_shot_value_trends=recent_shot_value_trends,
        recommendations=recommendations,
        trend_action_cards=trend_action_cards,
        course_baselines=course_adjustment_summary["course_baselines"],
        club_reliability_report=club_reliability_report,
        tee_strategy_comparison=tee_strategy_comparison,
        approach_strategy_comparison=approach_strategy_comparison,
        club_trends=final_club_trends,
        correlation_data=correlation_data
    )
