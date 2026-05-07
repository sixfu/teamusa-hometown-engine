from flask import Flask, jsonify, request
from flask_cors import CORS
from handlers.bigquery_handler import BigQueryHandler, OLYMPIC_SPORTS
from handlers.gemini_handler import GeminiHandler
from handlers.agent_handler import AgentHandler
import os
import random
import numpy as np

app = Flask(__name__)
CORS(app)

bq = BigQueryHandler()
gemini = GeminiHandler()
agent = AgentHandler(bq, gemini)

# ═══════════════════════════════════════════════════════════
# API Endpoint Definitions
# ═══════════════════════════════════════════════════════════

@app.route('/api/hometowns', methods=['GET'])
def get_hometowns():
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.get_all_hometowns(mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hometowns/by-state', methods=['GET'])
def get_hometowns_by_state():
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.get_hometowns_by_state(mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hometowns/search', methods=['GET'])
def search_hometown():
    city_name = request.args.get('city_name')
    state_code = request.args.get('state_code')
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.search_hometown(city_name, state_code, mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sports', methods=['GET'])
def get_sports():
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.get_all_sports(mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hometown/<hometown_id>', methods=['GET'])
def get_hometown_detail(hometown_id):
    mode = request.args.get('mode', 'olympic')
    try:
        hometown_data = bq.get_hometown_details(hometown_id, mode=mode)
        if not hometown_data:
            return jsonify({'success': False, 'error': 'Hometown not found'}), 404
        story = gemini.generate_hometown_story(hometown_data, mode=mode)
        hometown_data['story'] = story
        return jsonify({'success': True, 'data': hometown_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/region/sport-concentration', methods=['GET'])
def get_sport_concentration():
    city_name = request.args.get('city_name')
    state_code = request.args.get('state_code')
    mode = request.args.get('mode', 'olympic')
    if not city_name and not state_code:
        return jsonify({'success': False, 'error': 'city_name or state_code required'}), 400
    try:
        data = bq.get_sport_concentration(city_name, state_code, mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sports/year-counts', methods=['GET'])
def get_sport_year_counts():
    sport_name = request.args.get('sport_name')
    mode = request.args.get('mode', 'olympic')
    if not sport_name:
        return jsonify({'success': False, 'error': 'sport_name required'}), 400
    try:
        data = bq.get_sport_year_counts(sport_name, mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sports/heatmap', methods=['GET'])
def get_sport_heatmap():
    sport_name = request.args.get('sport_name')
    mode = request.args.get('mode', 'olympic')
    if not sport_name:
        return jsonify({'success': False, 'error': 'sport_name required'}), 400
    try:
        data = bq.get_sport_heatmap(sport_name, mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/compare', methods=['GET'])
def compare_regions():
    city1  = request.args.get('city1')
    state1 = request.args.get('state1')
    city2  = request.args.get('city2')
    state2 = request.args.get('state2')
    mode   = request.args.get('mode', 'olympic')
    if not (city1 or state1) or not (city2 or state2):
        return jsonify({'success': False, 'error': 'Two regions required'}), 400
    try:
        data = bq.get_region_comparison(city1, state1, city2, state2, mode=mode)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sport/heatmap-description', methods=['GET'])
def get_heatmap_description():
    sport_name = request.args.get('sport_name')
    mode = request.args.get('mode', 'olympic')
    if not sport_name:
        return jsonify({'success': False, 'error': 'sport_name required'}), 400
    try:
        heatmap = bq.get_sport_heatmap(sport_name, mode=mode)
        top5 = sorted(heatmap, key=lambda x: x.get('sport_athletes', 0), reverse=True)[:5]
        total = sum(h.get('sport_athletes', 0) for h in heatmap)
        result = gemini.generate_heatmap_description(sport_name, top5, total, mode=mode)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hometowns/observation', methods=['GET'])
def get_map_observation():
    mode = request.args.get('mode', 'olympic')
    try:
        hometowns = bq.get_all_hometowns(mode=mode)
        top10 = sorted(hometowns, key=lambda x: x.get('total_athletes', 0), reverse=True)[:10]
        total = sum(h.get('total_athletes', 0) for h in hometowns)
        observation = gemini.generate_map_observation(top10, total, mode=mode)
        return jsonify({'success': True, 'data': {'observation': observation}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/hometowns/observation', methods=['POST'])
def post_map_observation():
    data = request.get_json() or {}
    mode = data.get('mode', 'olympic')
    hometowns = data.get('hometowns', [])
    total = data.get('total_athletes', 0)
    try:
        observation = gemini.generate_map_observation(hometowns, total, mode=mode, focus_region=True)
        return jsonify({'success': True, 'data': {'observation': observation}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sport/animation', methods=['GET'])
def get_sport_animation():
    sport_name = request.args.get('sport_name')
    mode = request.args.get('mode', 'olympic')
    if not sport_name:
        return jsonify({'success': False, 'error': 'sport_name required'}), 400
    try:
        svg = gemini.generate_sport_animation(sport_name, mode=mode)
        return jsonify({'success': True, 'data': {'svg': svg}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sports/hubs', methods=['GET'])
def get_sport_hubs():
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.get_sport_hubs(mode=mode)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'mode': mode,
            'total_sports': len(OLYMPIC_SPORTS) if mode == 'olympic' else None,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sports/rank1-cities', methods=['GET'])
def get_rank1_cities_by_sport():
    mode = request.args.get('mode', 'olympic')
    try:
        data = bq.get_rank1_cities_by_sport(mode=mode)
        return jsonify({'success': True, 'data': data, 'count': len(data), 'mode': mode})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/rank1-raw', methods=['GET'])
def debug_rank1_raw():
    """Return top city-sport pairs with no thresholds — for diagnosing Sport Leaders."""
    mode = request.args.get('mode', 'olympic')
    sport = request.args.get('sport')
    try:
        data = bq.debug_rank1_raw(mode=mode, sport=sport)
        return jsonify({'success': True, 'data': data[:50], 'total_rows': len(data), 'mode': mode})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/sport-year-table', methods=['GET'])
def debug_sport_year_table():
    """Inspect actual column names and sample rows from athletes_counts_by_sport_year."""
    from handlers.bigquery_handler import Config
    try:
        query = f"SELECT * FROM `{Config.BQ_SPORT_YEAR_COUNTS_TABLE}` LIMIT 10"
        rows = bq.client.query(query).to_dataframe()
        return jsonify({
            'success': True,
            'columns': list(rows.columns),
            'sample_rows': rows.to_dict(orient='records'),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/cache-stats', methods=['GET'])
def cache_stats():
    stats = gemini.get_cache_stats()
    return jsonify({'success': True, 'data': stats})

@app.route('/api/debug/clear-cache', methods=['POST'])
def clear_cache():
    count = gemini.clear_cache()
    return jsonify({'success': True, 'message': f'Cleared {count} cached stories'})

@app.route('/api/agent/query', methods=['POST'])
def agent_query():
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    include_paralympics = bool(data.get('include_paralympics', True))
    history = data.get('history', [])
    if not question:
        return jsonify({'success': False, 'error': 'question is required'}), 400
    try:
        result = agent.answer_question(question, include_paralympics, history=history)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/find-matched-sports', methods=['POST'])
def find_matched_sports():
    data = request.get_json() or {}
    height = data.get('height')       # int/float, cm
    weight = data.get('weight')       # int/float, kg
    birth_city = (data.get('birth_city') or '').strip()
    birth_state = (data.get('birth_state') or '').strip()

    has_hw = height is not None and weight is not None
    has_city = bool(birth_city)
    has_state = bool(birth_state)

    try:
        df = bq.get_athletes_4predictsport()

        # Fill NaN in birth columns with empty string for safe string ops
        df['birth_city'] = df['birth_city'].fillna('')
        df['birth_state'] = df['birth_state'].fillna('')

        sport_freq = df['sport'].value_counts().to_dict()

        def _top3_by_score(scored_df):
            """Given df with '_score' column, return top-3 sports by min score (ties: alpha)."""
            sport_min = scored_df.groupby('sport')['_score'].min().reset_index()
            sport_min = sport_min.sort_values(['_score', 'sport'])
            return [
                {'sport': row['sport'], 'frequency': sport_freq.get(row['sport'], 0)}
                for _, row in sport_min.head(3).iterrows()
            ]

        def _random_sports(pool_df, n=3):
            available = pool_df['sport'].unique().tolist()
            selected = random.sample(available, min(n, len(available)))
            return [{'sport': s, 'frequency': sport_freq.get(s, 0)} for s in selected]

        def _safe_std(series):
            v = series.std()
            return float(v) if (v == v and v > 0) else 1.0  # guard NaN (NaN != NaN) and 0

        def _normalize_body_dist(df_hw):
            """Add Euclidean distance column '_score' to df_hw (z-score normalized)."""
            df_hw = df_hw.dropna(subset=['height', 'weight']).copy()
            h_mean, h_std = float(df_hw['height'].mean()), _safe_std(df_hw['height'])
            w_mean, w_std = float(df_hw['weight'].mean()), _safe_std(df_hw['weight'])
            user_nh = (float(height) - h_mean) / h_std
            user_nw = (float(weight) - w_mean) / w_std
            df_hw['_nh'] = (df_hw['height'] - h_mean) / h_std
            df_hw['_nw'] = (df_hw['weight'] - w_mean) / w_std
            df_hw['_score'] = np.sqrt((df_hw['_nh'] - user_nh) ** 2 + (df_hw['_nw'] - user_nw) ** 2)
            return df_hw

        if has_hw and has_city and has_state:
            # Combined: normalized body distance minus geo weight (lower = better match)
            df_hw = _normalize_body_dist(df)
            max_dist = df_hw['_score'].max() or 1
            df_hw['_norm_dist'] = df_hw['_score'] / max_dist

            city_lo = birth_city.lower()
            state_up = birth_state.upper()

            def _geo_weight(row):
                if row['birth_city'].lower() == city_lo and row['birth_state'].upper() == state_up:
                    return 1.0
                if row['birth_state'].upper() == state_up:
                    return 0.5
                return 0.0

            df_hw['_geo'] = df_hw.apply(_geo_weight, axis=1)
            df_hw['_score'] = df_hw['_norm_dist'] - df_hw['_geo']
            sports = _top3_by_score(df_hw)

        elif has_hw:
            # Body distance only
            df_hw = _normalize_body_dist(df)
            sports = _top3_by_score(df_hw)

        elif has_city and has_state:
            city_mask = (df['birth_city'].str.lower() == birth_city.lower()) & \
                        (df['birth_state'].str.upper() == birth_state.upper())
            city_df = df[city_mask]
            if len(city_df) > 0:
                sports = _random_sports(city_df)
            else:
                state_df = df[df['birth_state'].str.upper() == birth_state.upper()]
                pool = state_df if len(state_df) > 0 else df
                sports = _random_sports(pool)

        elif has_state:
            state_df = df[df['birth_state'].str.upper() == birth_state.upper()]
            pool = state_df if len(state_df) > 0 else df
            sports = _random_sports(pool)

        elif has_city:
            city_df = df[df['birth_city'].str.lower() == birth_city.lower()]
            pool = city_df if len(city_df) > 0 else df
            sports = _random_sports(pool)

        else:
            sports = _random_sports(df)

        return jsonify({'success': True, 'data': {'sports': sports}})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
