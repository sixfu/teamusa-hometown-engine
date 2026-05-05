from google.cloud import bigquery
from config import Config

def _pq(name, type_, value):
    return bigquery.ScalarQueryParameter(name, type_, value)

OLYMPIC_SPORTS = [
    # Summer Olympics
    '3x3 Basketball', 'Archery', 'Artistic Gymnastics', 'Artistic Swimming',
    'Athletics', 'Badminton', 'Basketball', 'Beach Volleyball', 'Boxing',
    'Breaking', 'Canoe Slalom', 'Canoe Sprint', 'Cycling BMX Freestyle',
    'Cycling BMX Racing', 'Cycling Mountain Bike', 'Cycling Road', 'Cycling Track',
    'Diving', 'Equestrian Dressage', 'Equestrian Eventing', 'Equestrian Jumping',
    'Fencing', 'Football', 'Golf', 'Handball', 'Hockey', 'Judo', 'Marathon Swimming',
    'Modern Pentathlon', 'Rhythmic Gymnastics', 'Rowing', 'Rugby Sevens', 'Sailing',
    'Shooting', 'Skateboarding', 'Sport Climbing', 'Surfing', 'Swimming',
    'Table Tennis', 'Taekwondo', 'Tennis', 'Trampolining', 'Triathlon', 'Volleyball',
    'Water Polo', 'Weightlifting', 'Wrestling',
    # Winter Olympics
    'Alpine Skiing', 'Biathlon', 'Bobsleigh', 'Cross Country Skiing', 'Curling',
    'Figure Skating', 'Freestyle Skiing', 'Ice Hockey', 'Luge', 'Nordic Combined',
    'Short Track Speed Skating', 'Skeleton', 'Ski Jumping', 'Snowboarding',
    'Speed Skating',
]

class BigQueryHandler:
    def __init__(self):
        self.client = bigquery.Client(project=Config.GCP_PROJECT_ID)

    def _tables(self, mode):
        """Return (athletes, hometowns, sports) table references for the given mode."""
        if mode == 'paralympic':
            return (Config.BQ_ATHLETES_TABLE_PARA,
                    Config.BQ_HOMETOWNS_TABLE_PARA,
                    Config.BQ_SPORTS_TABLE_PARA)
        return (Config.BQ_ATHLETES_TABLE,
                Config.BQ_HOMETOWNS_TABLE,
                Config.BQ_SPORTS_TABLE)

    def _sport_col(self, mode):
        """Column name for sport in the athletes table."""
        return 'sport' if mode == 'paralympic' else 'sport_clean'

    def _total_col(self, mode):
        """Column name for athlete count in the sports table."""
        return 'total_athletes' if mode == 'paralympic' else 'total_us_athletes'

    def get_all_hometowns(self, mode='olympic'):
        _, hometowns_tbl, _ = self._tables(mode)
        query = f"""
        SELECT
            hometown_id,
            city_name,
            state_code,
            latitude,
            longitude,
            total_athletes,
            region,
            elevation,
            distance_to_west_coast_km,
            distance_to_east_coast_km,
            distance_to_nearest_coast_km,
            climate_zone
        FROM `{hometowns_tbl}`
        ORDER BY total_athletes DESC
        """
        results = self.client.query(query).to_dataframe()
        return results.to_dict(orient='records')

    def get_hometowns_by_state(self, mode='olympic'):
        _, hometowns_tbl, _ = self._tables(mode)
        query = f"""
        SELECT
            state_code,
            SUM(total_athletes) as total_athletes_in_state,
            COUNT(*) as num_cities
        FROM `{hometowns_tbl}`
        GROUP BY state_code
        ORDER BY total_athletes_in_state DESC
        """
        results = self.client.query(query).to_dataframe()
        return results.to_dict(orient='records')

    def search_hometown(self, city_name=None, state_code=None, mode='olympic'):
        _, hometowns_tbl, _ = self._tables(mode)
        query = f"""
        SELECT
            hometown_id,
            city_name,
            state_code,
            latitude,
            longitude,
            total_athletes,
            region,
            elevation,
            distance_to_west_coast_km,
            distance_to_east_coast_km,
            distance_to_nearest_coast_km,
            climate_zone
        FROM `{hometowns_tbl}`
        WHERE 1=1
        """
        if city_name:
            query += f" AND LOWER(city_name) LIKE LOWER('%{city_name}%')"
        if state_code:
            query += f" AND state_code = '{state_code.upper()}'"
        query += " ORDER BY total_athletes DESC LIMIT 20"
        results = self.client.query(query).to_dataframe()
        return results.to_dict(orient='records')

    def get_all_sports(self, mode='olympic'):
        _, _, sports_tbl = self._tables(mode)
        total_col = self._total_col(mode)
        query = f"""
        SELECT
            sport_id,
            sport_name,
            {total_col} AS total_us_athletes
        FROM `{sports_tbl}`
        ORDER BY {total_col} DESC
        """
        results = self.client.query(query).to_dataframe()
        return results.to_dict(orient='records')

    def get_hometown_details(self, hometown_id, mode='olympic'):
        athletes_tbl, hometowns_tbl, _ = self._tables(mode)
        query = f"""
        SELECT
            hometown_id,
            city_name,
            state_code,
            latitude,
            longitude,
            total_athletes,
            region,
            elevation,
            distance_to_west_coast_km,
            distance_to_east_coast_km,
            distance_to_nearest_coast_km,
            climate_zone
        FROM `{hometowns_tbl}`
        WHERE hometown_id = '{hometown_id}'
        LIMIT 1
        """
        hometown = self.client.query(query).to_dataframe().to_dict(orient='records')
        if not hometown:
            return None

        hometown_data = hometown[0]
        city_name = hometown_data['city_name']
        state_code = hometown_data['state_code']

        sport_col = self._sport_col(mode)
        query_sports = f"""
        SELECT
            {sport_col} AS sport_name,
            COUNT(DISTINCT athlete_id) as count
        FROM `{athletes_tbl}`
        WHERE birth_city = '{city_name}' AND birth_state = '{state_code}'
        GROUP BY {sport_col}
        ORDER BY count DESC
        """
        try:
            top_sports = self.client.query(query_sports).to_dataframe().to_dict(orient='records')
            hometown_data['top_sports'] = top_sports
        except:
            hometown_data['top_sports'] = []

        return hometown_data

    def get_sport_concentration(self, city_name=None, state_code=None, mode='olympic'):
        athletes_tbl, _, _ = self._tables(mode)
        conditions, params = [], []
        if city_name:
            conditions.append("LOWER(birth_city) = LOWER(@city_name)")
            params.append(_pq("city_name", "STRING", city_name))
        if state_code:
            conditions.append("birth_state = @state_code")
            params.append(_pq("state_code", "STRING", state_code.upper()))

        sport_col = self._sport_col(mode)
        where = " AND ".join(conditions)
        query = f"""
        WITH national AS (
            SELECT {sport_col} AS sport_clean,
                   COUNT(DISTINCT athlete_id) AS national_count
            FROM `{athletes_tbl}`
            WHERE birth_state IS NOT NULL AND birth_state != ''
            GROUP BY {sport_col}
        ),
        national_total AS (
            SELECT SUM(national_count) AS total FROM national
        ),
        local_counts AS (
            SELECT {sport_col} AS sport_clean, COUNT(DISTINCT athlete_id) AS local_count
            FROM `{athletes_tbl}`
            WHERE {where}
            GROUP BY {sport_col}
        ),
        local_total AS (
            SELECT SUM(local_count) AS total FROM local_counts
        )
        SELECT
            lc.sport_clean                                                        AS sport_name,
            lc.local_count,
            lt.total                                                              AS local_total,
            n.national_count,
            nt.total                                                              AS total_national,
            ROUND(SAFE_DIVIDE(lc.local_count, lt.total) * 100, 1)               AS local_pct,
            ROUND(SAFE_DIVIDE(n.national_count, nt.total) * 100, 1)             AS national_pct,
            ROUND(SAFE_DIVIDE(
                SAFE_DIVIDE(lc.local_count, lt.total),
                SAFE_DIVIDE(n.national_count, nt.total)
            ), 2)                                                                 AS concentration_ratio
        FROM local_counts lc
        CROSS JOIN local_total lt
        JOIN national n ON lc.sport_clean = n.sport_clean
        CROSS JOIN national_total nt
        WHERE lc.local_count >= 2
        ORDER BY concentration_ratio DESC
        LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        return self.client.query(query, job_config=job_config).to_dataframe().to_dict(orient='records')

    def get_sport_year_counts(self, sport_name, mode='olympic'):
        """Return athlete counts per year for a sport from the precomputed table.
        Returns [] if the sport has no rows in the table."""
        table = Config.BQ_SPORT_YEAR_COUNTS_TABLE_PARA if mode == 'paralympic' else Config.BQ_SPORT_YEAR_COUNTS_TABLE
        query = f"""
        SELECT year, num_athletes
        FROM `{table}`
        WHERE sport_name = @sport_name
        ORDER BY year
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            _pq('sport_name', 'STRING', sport_name)
        ])
        rows = self.client.query(query, job_config=job_config).to_dataframe().to_dict(orient='records')
        return rows

    def get_sport_heatmap(self, sport_name, mode='olympic'):
        athletes_tbl, hometowns_tbl, _ = self._tables(mode)
        sport_col = self._sport_col(mode)
        query = f"""
        WITH city_matched AS (
            -- Athletes that can be pinned to an exact city in the hometowns table
            SELECT DISTINCT a.athlete_id
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} = @sport_name
                AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL
        ),
        city_results AS (
            SELECT
                h.hometown_id,
                h.city_name,
                h.state_code,
                h.latitude,
                h.longitude,
                COUNT(DISTINCT a.athlete_id) AS sport_athletes,
                'city' AS match_level
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} = @sport_name
                AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL
            GROUP BY h.hometown_id, h.city_name, h.state_code, h.latitude, h.longitude
        ),
        state_centroids AS (
            -- Derive state centre from existing hometowns rather than hard-coding coords
            SELECT
                state_code,
                AVG(latitude)  AS latitude,
                AVG(longitude) AS longitude
            FROM `{hometowns_tbl}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY state_code
        ),
        state_results AS (
            -- Athletes not matched at city level but who have a known state
            SELECT
                CONCAT('STATE_', a.birth_state) AS hometown_id,
                a.birth_state                   AS city_name,
                a.birth_state                   AS state_code,
                sc.latitude,
                sc.longitude,
                COUNT(DISTINCT a.athlete_id)    AS sport_athletes,
                'state'                         AS match_level
            FROM `{athletes_tbl}` a
            JOIN state_centroids sc ON a.birth_state = sc.state_code
            LEFT JOIN city_matched cm ON a.athlete_id = cm.athlete_id
            WHERE a.{sport_col} = @sport_name
                AND a.birth_state IS NOT NULL
                AND a.birth_state != ''
                AND cm.athlete_id IS NULL
            GROUP BY a.birth_state, sc.latitude, sc.longitude
        )
        SELECT * FROM city_results
        UNION ALL
        SELECT * FROM state_results
        ORDER BY sport_athletes DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[_pq("sport_name", "STRING", sport_name)]
        )
        return self.client.query(query, job_config=job_config).to_dataframe().to_dict(orient='records')

    def get_rank1_cities_by_sport(self, mode='olympic'):
        athletes_tbl, hometowns_tbl, _ = self._tables(mode)
        sport_col = self._sport_col(mode)

        # Thresholds per mode
        if mode == 'paralympic':
            min_sport_count   = 2
            min_concentration = 2.0
        else:
            min_sport_count   = 3
            min_concentration = 2.0

        query = f"""
        WITH national AS (
            SELECT {sport_col} AS sport_name,
                   COUNT(DISTINCT athlete_id) AS national_count
            FROM `{athletes_tbl}`
            WHERE birth_state IS NOT NULL AND birth_state != ''
              AND {sport_col} IS NOT NULL AND {sport_col} != ''
            GROUP BY {sport_col}
        ),
        national_total AS (
            SELECT SUM(national_count) AS total FROM national
        ),
        city_sport_counts AS (
            SELECT
                h.hometown_id,
                h.city_name,
                h.state_code,
                h.latitude,
                h.longitude,
                h.region,
                h.elevation,
                h.climate_zone,
                a.{sport_col} AS sport_name,
                COUNT(DISTINCT a.athlete_id) AS sport_count
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} IS NOT NULL
                AND a.{sport_col} != ''
                AND h.latitude IS NOT NULL
                AND h.longitude IS NOT NULL
            GROUP BY
                h.hometown_id, h.city_name, h.state_code, h.latitude, h.longitude,
                h.region, h.elevation, h.climate_zone, a.{sport_col}
        ),
        city_totals AS (
            -- Sum all sports per city for a consistent denominator
            SELECT hometown_id, SUM(sport_count) AS city_total
            FROM city_sport_counts
            GROUP BY hometown_id
        ),
        qualified AS (
            -- Pre-filter by min athlete count BEFORE ranking so 1-athlete
            -- anomaly cities never reach rank-1
            SELECT csc.*, ct.city_total
            FROM city_sport_counts csc
            JOIN city_totals ct ON csc.hometown_id = ct.hometown_id
            WHERE csc.sport_count >= {min_sport_count}
        ),
        with_ratio AS (
            SELECT
                q.*,
                ROUND(SAFE_DIVIDE(
                    SAFE_DIVIDE(q.sport_count, q.city_total),
                    SAFE_DIVIDE(n.national_count, nt.total)
                ), 2) AS concentration_ratio,
                RANK() OVER (
                    PARTITION BY q.sport_name
                    ORDER BY SAFE_DIVIDE(
                        SAFE_DIVIDE(q.sport_count, q.city_total),
                        SAFE_DIVIDE(n.national_count, nt.total)
                    ) DESC
                ) AS conc_rank,
                RANK() OVER (
                    PARTITION BY q.sport_name
                    ORDER BY q.sport_count DESC
                ) AS count_rank
            FROM qualified q
            JOIN national n ON q.sport_name = n.sport_name
            CROSS JOIN national_total nt
        )
        SELECT
            sport_name,
            hometown_id,
            city_name,
            state_code,
            latitude,
            longitude,
            city_total AS total_athletes,
            region,
            elevation,
            climate_zone,
            sport_count,
            concentration_ratio,
            conc_rank,
            count_rank
        FROM with_ratio
        WHERE conc_rank <= 3 OR count_rank <= 3
        ORDER BY sport_name
        """
        rows = self.client.query(query).to_dataframe().to_dict(orient='records')

        # Hub = city that appears in BOTH top-3 by concentration AND top-3 by count
        conc_top3 = {}   # sport -> set of hometown_ids
        count_top3 = {}  # sport -> set of hometown_ids
        city_data = {}   # (sport, hometown_id) -> row

        for row in rows:
            sport = row['sport_name']
            hid = row['hometown_id']
            if sport not in conc_top3:
                conc_top3[sport] = set()
                count_top3[sport] = set()
            if int(row['conc_rank']) <= 3:
                conc_top3[sport].add(hid)
            if int(row['count_rank']) <= 3:
                count_top3[sport].add(hid)
            city_data[(sport, hid)] = row

        selected = []
        for sport in conc_top3:
            hub_ids = conc_top3[sport] & count_top3.get(sport, set())
            for hid in hub_ids:
                row = city_data[(sport, hid)]
                selected.append({k: v for k, v in row.items()
                                 if k not in ('conc_rank', 'count_rank')})

        selected.sort(key=lambda x: x.get('concentration_ratio', 0), reverse=True)
        return selected

    def get_sport_hubs(self, mode='olympic'):
        """Return one hub city per sport using the 4-condition definition."""
        athletes_tbl, hometowns_tbl, _ = self._tables(mode)
        sport_col = self._sport_col(mode)

        if mode == 'paralympic':
            min_city_athletes = 2
            min_total_athletes = 5
            min_hub_pct = 0.10
            min_concentration = 2.5
        else:
            min_city_athletes = 3
            min_total_athletes = 10
            min_hub_pct = 0.05
            min_concentration = 2.0

        query_params = []
        if mode == 'olympic':
            sport_filter = f'AND a.{sport_col} IN UNNEST(@sports)'
            nat_sport_filter = f'AND {sport_col} IN UNNEST(@sports)'
            query_params.append(bigquery.ArrayQueryParameter('sports', 'STRING', OLYMPIC_SPORTS))
        else:
            sport_filter = ''
            nat_sport_filter = ''

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        query = f"""
        WITH national AS (
            SELECT {sport_col} AS sport_name,
                   COUNT(DISTINCT athlete_id) AS national_count
            FROM `{athletes_tbl}`
            WHERE birth_state IS NOT NULL AND birth_state != ''
              AND {sport_col} IS NOT NULL AND {sport_col} != ''
              {nat_sport_filter}
            GROUP BY {sport_col}
        ),
        national_total AS (
            SELECT SUM(national_count) AS total FROM national
        ),
        city_sport_counts AS (
            SELECT
                h.hometown_id,
                h.city_name,
                h.state_code,
                h.latitude,
                h.longitude,
                h.region,
                h.elevation,
                h.climate_zone,
                a.{sport_col} AS sport_name,
                COUNT(DISTINCT a.athlete_id) AS sport_count
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} IS NOT NULL AND a.{sport_col} != ''
              {sport_filter}
              AND h.latitude IS NOT NULL
              AND h.longitude IS NOT NULL
            GROUP BY
                h.hometown_id, h.city_name, h.state_code, h.latitude, h.longitude,
                h.region, h.elevation, h.climate_zone, a.{sport_col}
        ),
        city_totals AS (
            SELECT hometown_id, SUM(sport_count) AS city_total
            FROM city_sport_counts
            GROUP BY hometown_id
        ),
        qualified AS (
            -- Condition 1: min athletes in city for this sport
            SELECT csc.*, ct.city_total
            FROM city_sport_counts csc
            JOIN city_totals ct ON csc.hometown_id = ct.hometown_id
            WHERE csc.sport_count >= {min_city_athletes}
        ),
        with_ratio AS (
            SELECT
                q.*,
                n.national_count,
                ROUND(SAFE_DIVIDE(
                    SAFE_DIVIDE(q.sport_count, q.city_total),
                    SAFE_DIVIDE(n.national_count, nt.total)
                ), 2) AS concentration_ratio,
                ROUND(SAFE_DIVIDE(q.sport_count, n.national_count), 4) AS hub_pct,
                RANK() OVER (
                    PARTITION BY q.sport_name
                    ORDER BY SAFE_DIVIDE(
                        SAFE_DIVIDE(q.sport_count, q.city_total),
                        SAFE_DIVIDE(n.national_count, nt.total)
                    ) DESC
                ) AS conc_rank
            FROM qualified q
            JOIN national n ON q.sport_name = n.sport_name
            CROSS JOIN national_total nt
        )
        SELECT
            sport_name,
            hometown_id,
            city_name,
            state_code,
            latitude,
            longitude,
            city_total AS total_athletes,
            region,
            elevation,
            climate_zone,
            sport_count,
            concentration_ratio,
            hub_pct,
            national_count AS total_sport_athletes
        FROM with_ratio
        WHERE conc_rank = 1
          AND national_count >= {min_total_athletes}      -- Condition 2
          AND hub_pct >= {min_hub_pct}                    -- Condition 3
          AND concentration_ratio >= {min_concentration}  -- Condition 4
        ORDER BY sport_name, sport_count DESC
        """

        rows = self.client.query(query, job_config=job_config).to_dataframe().to_dict(orient='records')

        # One hub per sport — first row wins (highest sport_count for rank ties)
        hubs = {}
        for row in rows:
            sport = row['sport_name']
            if sport not in hubs:
                hubs[sport] = row

        result = list(hubs.values())
        result.sort(key=lambda x: x.get('concentration_ratio', 0), reverse=True)
        return result

    def debug_rank1_raw(self, mode='olympic', sport=None):
        """Top city-sport combos by concentration ratio, no threshold filters."""
        athletes_tbl, hometowns_tbl, _ = self._tables(mode)
        sport_col = self._sport_col(mode)
        sport_filter = f"AND a.{sport_col} = @sport_name" if sport else ""
        job_config = bigquery.QueryJobConfig(
            query_parameters=[_pq("sport_name", "STRING", sport)] if sport else []
        )
        query = f"""
        WITH national AS (
            SELECT {sport_col} AS sport_name,
                   COUNT(DISTINCT athlete_id) AS national_count
            FROM `{athletes_tbl}`
            WHERE birth_state IS NOT NULL AND birth_state != ''
              AND {sport_col} IS NOT NULL AND {sport_col} != ''
            GROUP BY {sport_col}
        ),
        national_total AS (SELECT SUM(national_count) AS total FROM national),
        all_city_sport_counts AS (
            -- All sports per city for correct denominator
            SELECT
                h.hometown_id,
                a.{sport_col} AS sport_name,
                COUNT(DISTINCT a.athlete_id) AS sport_count
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} IS NOT NULL AND a.{sport_col} != ''
                AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL
            GROUP BY h.hometown_id, a.{sport_col}
        ),
        city_totals AS (
            SELECT hometown_id, SUM(sport_count) AS city_total
            FROM all_city_sport_counts GROUP BY hometown_id
        ),
        filtered_sport AS (
            -- The specific sport rows we care about
            SELECT
                h.hometown_id, h.city_name, h.state_code,
                a.{sport_col} AS sport_name,
                COUNT(DISTINCT a.athlete_id) AS sport_count
            FROM `{athletes_tbl}` a
            JOIN `{hometowns_tbl}` h
                ON LOWER(a.birth_city) = LOWER(h.city_name)
                AND a.birth_state = h.state_code
            WHERE a.{sport_col} IS NOT NULL AND a.{sport_col} != ''
                AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL
                {sport_filter}
            GROUP BY h.hometown_id, h.city_name, h.state_code, a.{sport_col}
        )
        SELECT
            fs.city_name, fs.state_code, fs.sport_name,
            fs.sport_count, ct.city_total,
            ROUND(SAFE_DIVIDE(
                SAFE_DIVIDE(fs.sport_count, ct.city_total),
                SAFE_DIVIDE(n.national_count, nt.total)
            ), 2) AS concentration_ratio
        FROM filtered_sport fs
        JOIN city_totals ct ON fs.hometown_id = ct.hometown_id
        JOIN national n ON fs.sport_name = n.sport_name
        CROSS JOIN national_total nt
        ORDER BY concentration_ratio DESC
        LIMIT 100
        """
        return self.client.query(query, job_config=job_config).to_dataframe().to_dict(orient='records')

    def get_region_comparison(self, city1=None, state1=None, city2=None, state2=None, mode='olympic'):
        athletes_tbl, _, _ = self._tables(mode)
        sport_col = self._sport_col(mode)

        def query_region(city, state):
            conditions, params = [], []
            if city:
                conditions.append("LOWER(birth_city) = LOWER(@city_name)")
                params.append(_pq("city_name", "STRING", city))
            if state:
                conditions.append("birth_state = @state_code")
                params.append(_pq("state_code", "STRING", state.upper()))
            where = " AND ".join(conditions)
            q = f"""
            SELECT {sport_col} AS sport_name, COUNT(DISTINCT athlete_id) AS athlete_count
            FROM `{athletes_tbl}`
            WHERE {where}
                AND {sport_col} IS NOT NULL
                AND {sport_col} != ''
            GROUP BY {sport_col}
            ORDER BY athlete_count DESC
            LIMIT 30
            """
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            return self.client.query(q, job_config=job_config).to_dataframe().to_dict(orient='records')

        label1 = ", ".join(filter(None, [city1, state1]))
        label2 = ", ".join(filter(None, [city2, state2]))
        return {
            'region1': {'label': label1, 'sports': query_region(city1, state1)},
            'region2': {'label': label2, 'sports': query_region(city2, state2)},
        }
