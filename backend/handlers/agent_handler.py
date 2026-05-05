import re

# Common US state abbreviations for mention detection
_STATE_CODES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY','DC',
}

_GENERATION_CONFIG = {'temperature': 0.3}   # low creativity → high factual accuracy


def _dedup(lst):
    seen, out = set(), []
    for x in lst:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


class AgentHandler:
    """
    Agentic AI that gathers context from all BigQuery tables and answers
    questions with Gemini, supporting short-term conversation memory.
    """

    def __init__(self, bq_handler, gemini_handler):
        self.bq    = bq_handler
        self.model = gemini_handler.model  # reuse already-configured model

    # ── Public API ────────────────────────────────────────────────────────────

    def answer_question(
        self,
        question: str,
        include_paralympics: bool = True,
        history=None,
    ) -> dict:
        context = self._gather_context(question, include_paralympics)
        answer  = self._generate_answer(question, context, history or [])

        # Confidence: high when sport/city/year-specific data was fetched
        oly = context['olympic']
        has_specific = any(
            k in oly
            for k in ('sport_heatmap', 'year_counts', 'multi_year_counts',
                      'city_search', 'hubs', 'rank1', 'sport_concentration', 'by_state')
        )
        confidence = 'high' if has_specific else 'medium'

        return {
            'answer':     answer,
            'sources':    context['sources'],
            'data_used':  {
                **context['stats'],
                'tables_queried': context['tables_queried'],
            },
            'confidence': confidence,
        }

    # ── Intent parsing ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_intents(question: str) -> dict:
        q = question.lower()

        # Detect a specific 4-digit year (1950-2029)
        year_m = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', question)
        detected_year = int(year_m.group(1)) if year_m else None

        # Trend/time-series signal: explicit keywords OR a specific year in the question
        trend_kws = [
            'grow', 'trend', 'increas', 'declin', 'history', 'over time',
            'time series', 'timeline', 'since', 'by year', 'peak', 'most ever',
            'fewest', 'highest year', 'lowest year',
        ]
        wants_trend = detected_year is not None or any(kw in q for kw in trend_kws)

        hub_kws  = ['hub', 'cluster', 'hotspot', 'concentrat', 'lead', 'top city',
                    'top cities', 'best city', 'dominant']
        rank_kws = ['rank', 'number one', 'leading city', 'top city for', 'best city for',
                    '#1', 'first place']
        state_kws = ['state', 'region', 'which state', 'by state', 'most athletes by state']
        para_kws  = ['paralympic', 'para ', 'adaptive', 'wheelchair', 'disabled']
        cmp_kws   = ['compare', 'versus', ' vs ', 'both', 'difference',
                     'olympic and para', 'para and olympic']

        # State code detection
        detected_state = None
        for token in re.findall(r'\b[A-Z]{2}\b', question):
            if token in _STATE_CODES:
                detected_state = token
                break

        # City detection heuristic
        detected_city = None
        city_m = re.search(
            r'(?:city of |in |from |about )([\w\s]+?)(?:,\s*[A-Z]{2}|\s+athletes|\s+hometowns|$)',
            question, re.IGNORECASE,
        )
        if city_m:
            candidate = city_m.group(1).strip()
            if len(candidate) > 2 and candidate.lower() not in ('the','all','top','most','which','how','what'):
                detected_city = candidate

        return {
            'q':             q,
            'detected_year': detected_year,
            'wants_trend':   wants_trend,
            'wants_hub':     any(kw in q for kw in hub_kws),
            'wants_rank':    any(kw in q for kw in rank_kws),
            'wants_state':   any(kw in q for kw in state_kws) or bool(detected_state),
            'wants_para':    any(kw in q for kw in para_kws),
            'wants_cmp':     any(kw in q for kw in cmp_kws),
            'detected_state': detected_state,
            'detected_city':  detected_city,
        }

    # ── Context gathering ─────────────────────────────────────────────────────

    def _gather_context(self, question: str, include_paralympics: bool) -> dict:
        intents = self._parse_intents(question)
        q             = intents['q']
        detected_year = intents['detected_year']
        tables_queried = []
        sources        = []

        context = {
            'olympic':       {},
            'paralympic':    {},
            'sources':       sources,
            'tables_queried': tables_queried,
            'intents':       intents,
            'stats': {
                'olympic_count': 0, 'paralympic_count': 0,
                'total_athletes': 0, 'states_covered': 0, 'regions_covered': 0,
            },
        }

        # ── Always: Olympic base data ─────────────────────────────────────────
        oly_hometowns = self.bq.get_all_hometowns(mode='olympic')
        oly_sports    = self.bq.get_all_sports(mode='olympic')
        oly_total     = sum(h.get('total_athletes', 0) for h in oly_hometowns)

        context['olympic']['hometowns']      = sorted(oly_hometowns, key=lambda x: x.get('total_athletes', 0), reverse=True)[:20]
        context['olympic']['sports']         = oly_sports
        context['olympic']['total_athletes'] = oly_total
        context['stats']['olympic_count']    = oly_total
        tables_queried.extend(['athletes', 'hometowns', 'sports'])
        sources.extend(['athletes table', 'hometowns table', 'sports table'])

        # ── Detect sport mention ──────────────────────────────────────────────
        detected_sport = None
        for s in oly_sports:
            if s.get('sport_name', '').lower() in q:
                detected_sport = s['sport_name']
                break

        # ── Sport heatmap ─────────────────────────────────────────────────────
        if detected_sport:
            context['olympic']['sport_heatmap'] = self.bq.get_sport_heatmap(detected_sport, mode='olympic')[:10]
            tables_queried.extend(['athletes', 'hometowns'])
            sources.append(f'{detected_sport} geographic distribution (athletes + hometowns)')

        # ── Year / trend data (athletes_counts_by_sport_year) ─────────────────
        # Triggered by: specific year mentioned, trend keywords, or "how many ... [year]"
        if intents['wants_trend']:
            if detected_sport:
                all_yr = self.bq.get_sport_year_counts(detected_sport, mode='olympic')
                context['olympic']['year_counts']    = all_yr
                context['olympic']['detected_year']  = detected_year
                # Pre-filter the specific year for prominence
                if detected_year:
                    exact = [r for r in all_yr if r.get('year') == detected_year]
                    context['olympic']['year_at_focus'] = exact
                tables_queried.append('athletes_counts_by_sport_year')
                sources.append('athletes_counts_by_sport_year table')
            else:
                # Fetch top-5 sports and, if a year is specified, filter to that year
                top5 = sorted(oly_sports, key=lambda x: x.get('total_us_athletes', x.get('total_athletes', 0)), reverse=True)[:5]
                multi = {}
                for s in top5:
                    rows = self.bq.get_sport_year_counts(s['sport_name'], mode='olympic')
                    if rows:
                        if detected_year:
                            # Keep full series so Gemini can also show context; mark year
                            multi[s['sport_name']] = rows
                        else:
                            multi[s['sport_name']] = rows
                if multi:
                    context['olympic']['multi_year_counts'] = multi
                    context['olympic']['detected_year']     = detected_year
                    tables_queried.append('athletes_counts_by_sport_year')
                    sources.append('athletes_counts_by_sport_year table')

        # ── Sport hubs ────────────────────────────────────────────────────────
        if intents['wants_hub']:
            context['olympic']['hubs'] = self.bq.get_sport_hubs(mode='olympic')[:12]
            tables_queried.extend(['athletes', 'hometowns'])
            sources.append('sport hubs analysis (athletes + hometowns)')

        # ── Top-ranked city per sport ─────────────────────────────────────────
        if intents['wants_rank']:
            context['olympic']['rank1'] = self.bq.get_rank1_cities_by_sport(mode='olympic')[:20]
            tables_queried.extend(['athletes', 'hometowns'])
            sources.append('rank-1 cities by sport (athletes + hometowns)')

        # ── State-level aggregation ───────────────────────────────────────────
        if intents['wants_state']:
            context['olympic']['by_state'] = self.bq.get_hometowns_by_state(mode='olympic')
            tables_queried.append('hometowns')
            sources.append('hometowns table (by state)')

        # ── City-specific search & sport concentration ────────────────────────
        detected_city  = intents['detected_city']
        detected_state = intents['detected_state']
        if detected_city or detected_state:
            sr = self.bq.search_hometown(city_name=detected_city, state_code=detected_state, mode='olympic')
            if sr:
                context['olympic']['city_search'] = sr[:5]
                tables_queried.append('hometowns')
                sources.append('hometowns table (city search)')

            if not detected_sport:
                conc = self.bq.get_sport_concentration(city_name=detected_city, state_code=detected_state, mode='olympic')
                if conc:
                    context['olympic']['sport_concentration'] = conc[:8]
                    tables_queried.append('athletes')
                    sources.append('athletes table (sport concentration)')

        # ── Paralympic data ───────────────────────────────────────────────────
        if include_paralympics and (intents['wants_para'] or intents['wants_cmp']):
            para_hometowns = self.bq.get_all_hometowns(mode='paralympic')
            para_sports    = self.bq.get_all_sports(mode='paralympic')
            para_total     = sum(h.get('total_athletes', 0) for h in para_hometowns)

            context['paralympic']['hometowns']      = sorted(para_hometowns, key=lambda x: x.get('total_athletes', 0), reverse=True)[:15]
            context['paralympic']['sports']         = para_sports
            context['paralympic']['total_athletes'] = para_total
            context['stats']['paralympic_count']    = para_total
            tables_queried.extend(['athletes_para', 'hometowns_para', 'sports_para'])
            sources.extend(['athletes_para table', 'hometowns_para table', 'sports_para table'])

            if detected_sport:
                para_map   = {s['sport_name'].lower(): s['sport_name'] for s in para_sports}
                para_sport = para_map.get(detected_sport.lower())
                if para_sport:
                    context['paralympic']['sport_heatmap'] = self.bq.get_sport_heatmap(para_sport, mode='paralympic')[:10]

            if intents['wants_trend']:
                if detected_sport:
                    para_yr = self.bq.get_sport_year_counts(detected_sport, mode='paralympic')
                    context['paralympic']['year_counts']   = para_yr
                    context['paralympic']['detected_year'] = detected_year
                    if detected_year:
                        context['paralympic']['year_at_focus'] = [r for r in para_yr if r.get('year') == detected_year]
                    tables_queried.append('para_athletes_counts_by_sport_year')
                    sources.append('para_athletes_counts_by_sport_year table')
                else:
                    top5p  = sorted(para_sports, key=lambda x: x.get('total_athletes', 0), reverse=True)[:5]
                    multi_p = {}
                    for s in top5p:
                        rows = self.bq.get_sport_year_counts(s['sport_name'], mode='paralympic')
                        if rows:
                            multi_p[s['sport_name']] = rows
                    if multi_p:
                        context['paralympic']['multi_year_counts'] = multi_p
                        context['paralympic']['detected_year']     = detected_year
                        tables_queried.append('para_athletes_counts_by_sport_year')
                        sources.append('para_athletes_counts_by_sport_year table')

            if intents['wants_hub']:
                context['paralympic']['hubs'] = self.bq.get_sport_hubs(mode='paralympic')[:10]

            if intents['wants_state']:
                context['paralympic']['by_state'] = self.bq.get_hometowns_by_state(mode='paralympic')
                tables_queried.append('hometowns_para')
                sources.append('hometowns_para table (by state)')

        # ── Aggregate stats ───────────────────────────────────────────────────
        context['stats']['total_athletes']  = context['stats']['olympic_count'] + context['stats']['paralympic_count']
        context['stats']['states_covered']  = len({h.get('state_code') for h in oly_hometowns if h.get('state_code')})
        context['stats']['regions_covered'] = len({h.get('region') for h in oly_hometowns if h.get('region')})

        context['tables_queried'] = _dedup(tables_queried)
        context['sources']        = _dedup(sources) + ['Gemini AI insights']
        return context

    # ── Answer generation ─────────────────────────────────────────────────────

    def _generate_answer(self, question: str, context: dict, history: list) -> str:
        oly      = context['olympic']
        para     = context.get('paralympic', {})
        intents  = context.get('intents', {})
        focus_yr = intents.get('detected_year')

        # Format Olympic hometowns
        hometowns_text = '\n'.join(
            f"  {i+1}. {h.get('city_name','?')}, {h.get('state_code','')} — "
            f"{h.get('total_athletes',0)} athletes | "
            f"region: {h.get('region','unknown')} | "
            f"elevation: {h.get('elevation','N/A')}m | "
            f"climate: {h.get('climate_zone','unknown')}"
            for i, h in enumerate(oly.get('hometowns', [])[:15])
        )

        sports_text = ', '.join(
            f"{s['sport_name']} ({s.get('total_us_athletes', s.get('total_athletes', 0))})"
            for s in sorted(oly.get('sports', []), key=lambda x: x.get('total_us_athletes', x.get('total_athletes', 0)), reverse=True)[:20]
        )

        extra = ''

        # Sport heatmap
        if 'sport_heatmap' in oly:
            lines = '\n'.join(
                f"  {h.get('city_name') or h.get('state_code','?')}, {h.get('state_code','')} — {h.get('sport_athletes',0)} athletes"
                for h in oly['sport_heatmap'][:10]
            )
            extra += f"\nSPORT GEOGRAPHIC DATA (athletes + hometowns tables):\n{lines}\n"

        # Year / trend data — show ALL years so Gemini can locate any specific year
        if 'year_counts' in oly and oly['year_counts']:
            all_pts = ', '.join(f"{r['year']}: {r['num_athletes']}" for r in oly['year_counts'])
            extra += f"\nYEAR-BY-YEAR COUNTS (athletes_counts_by_sport_year table) — ALL YEARS:\n  {all_pts}\n"
            # Highlight specific year prominently so Gemini doesn't miss it
            focus = oly.get('year_at_focus')
            if focus:
                extra += f"  *** YEAR {focus_yr} = {focus[0]['num_athletes']} athletes ***\n"
            elif focus_yr:
                extra += f"  *** NOTE: Year {focus_yr} has NO data in athletes_counts_by_sport_year ***\n"

        if 'multi_year_counts' in oly:
            yr_label = f" (filtered to year {focus_yr})" if focus_yr else " (last 8 data points each)"
            extra += f"\nMULTI-SPORT YEAR DATA (athletes_counts_by_sport_year table){yr_label}:\n"
            for sp, rows in oly['multi_year_counts'].items():
                if focus_yr:
                    rel = [r for r in rows if r['year'] == focus_yr]
                    if rel:
                        extra += f"  {sp}: {rel[0]['num_athletes']} athletes in {focus_yr}\n"
                    else:
                        recent = ', '.join(f"{r['year']}: {r['num_athletes']}" for r in rows[-5:])
                        extra += f"  {sp}: no data for {focus_yr}. Recent: {recent}\n"
                else:
                    pts = ', '.join(f"{r['year']}: {r['num_athletes']}" for r in rows[-8:])
                    extra += f"  {sp}: {pts}\n"

        # Hubs
        if 'hubs' in oly:
            hub_lines = '\n'.join(
                f"  {h.get('city_name','?')}, {h.get('state_code','')} — excels in {h.get('sport_count',0)} sports, {h.get('total_athletes',0)} total athletes"
                for h in oly['hubs'][:12]
            )
            extra += f"\nSPORT HUBS (cities excelling across multiple sports):\n{hub_lines}\n"

        # Rank-1 cities
        if 'rank1' in oly:
            rank_lines = '\n'.join(
                f"  {r.get('sport_name','?')}: {r.get('city_name','?')}, {r.get('state_code','')} ({r.get('sport_count',0)} athletes)"
                for r in oly['rank1'][:15]
            )
            extra += f"\nTOP CITY PER SPORT:\n{rank_lines}\n"

        # By state
        if 'by_state' in oly:
            state_lines = '\n'.join(
                f"  {r.get('state_code','?')}: {r.get('total_athletes_in_state',0)} athletes, {r.get('num_cities',0)} cities"
                for r in sorted(oly['by_state'], key=lambda x: x.get('total_athletes_in_state',0), reverse=True)[:15]
            )
            extra += f"\nATHLETES BY STATE:\n{state_lines}\n"

        # City search
        if 'city_search' in oly:
            city_lines = '\n'.join(
                f"  {r.get('city_name','?')}, {r.get('state_code','')} — {r.get('total_athletes',0)} athletes | "
                f"region: {r.get('region','?')} | elevation: {r.get('elevation','?')}m | climate: {r.get('climate_zone','?')}"
                for r in oly['city_search']
            )
            extra += f"\nCITY SEARCH RESULTS:\n{city_lines}\n"

        # Sport concentration
        if 'sport_concentration' in oly:
            conc_lines = '\n'.join(
                f"  {r.get('sport_name','?')}: {r.get('local_count',0)} local vs {r.get('national_count',0)} national "
                f"(concentration ratio: {r.get('concentration_ratio','?')}x)"
                for r in oly['sport_concentration'][:8]
            )
            extra += f"\nSPORT CONCENTRATION FOR LOCATION:\n{conc_lines}\n"

        # Paralympic section
        para_section = ''
        if para.get('hometowns'):
            para_towns = '\n'.join(
                f"  {i+1}. {h.get('city_name','?')}, {h.get('state_code','')} — {h.get('total_athletes',0)} athletes"
                for i, h in enumerate(para['hometowns'][:12])
            )
            para_sports_text = ', '.join(
                f"{s['sport_name']} ({s.get('total_athletes',0)})"
                for s in sorted(para.get('sports',[]), key=lambda x: x.get('total_athletes',0), reverse=True)[:12]
            )
            para_section = (
                f"\nPARALYMPIC DATA (athletes_para + hometowns_para + sports_para tables):\n"
                f"Total Paralympic athletes: {para.get('total_athletes', 0)}\n"
                f"Top Paralympic hometowns:\n{para_towns}\n"
                f"Paralympic sports: {para_sports_text}\n"
            )
            if 'sport_heatmap' in para:
                ph = '\n'.join(
                    f"  {h.get('city_name') or h.get('state_code','?')}, {h.get('state_code','')} — {h.get('sport_athletes',0)} athletes"
                    for h in para['sport_heatmap'][:8]
                )
                para_section += f"Paralympic sport geographic data:\n{ph}\n"

            if 'year_counts' in para and para['year_counts']:
                pts = ', '.join(f"{r['year']}: {r['num_athletes']}" for r in para['year_counts'])
                para_section += f"Paralympic year counts (ALL YEARS): {pts}\n"
                pf = para.get('year_at_focus')
                if pf:
                    para_section += f"  *** YEAR {focus_yr} = {pf[0]['num_athletes']} Paralympic athletes ***\n"
                elif focus_yr:
                    para_section += f"  *** NOTE: Year {focus_yr} has NO Paralympic data ***\n"

            if 'multi_year_counts' in para:
                para_section += "Paralympic sport trends:\n"
                for sp, rows in para['multi_year_counts'].items():
                    if rows:
                        if focus_yr:
                            rel = [r for r in rows if r['year'] == focus_yr]
                            val = str(rel[0]['num_athletes']) if rel else 'no data'
                            para_section += f"  {sp} in {focus_yr}: {val}\n"
                        else:
                            pts = ', '.join(f"{r['year']}: {r['num_athletes']}" for r in rows[-5:])
                            para_section += f"  {sp}: {pts}\n"

            if 'hubs' in para:
                ph = '\n'.join(
                    f"  {h.get('city_name','?')}, {h.get('state_code','')} — {h.get('sport_count',0)} sports"
                    for h in para['hubs'][:8]
                )
                para_section += f"Paralympic hubs:\n{ph}\n"

            if 'by_state' in para:
                st = '\n'.join(
                    f"  {r.get('state_code','?')}: {r.get('total_athletes_in_state',0)} athletes"
                    for r in sorted(para['by_state'], key=lambda x: x.get('total_athletes_in_state',0), reverse=True)[:10]
                )
                para_section += f"Paralympic by state:\n{st}\n"

        # Conversation history section
        history_section = ''
        if history:
            turns = [
                f"{'User' if m.get('role') == 'user' else 'Agent'}: {m.get('content','')[:300]}"
                for m in history[-6:]
            ]
            history_section = "PRIOR CONVERSATION (use to resolve follow-up references):\n" + '\n'.join(turns) + "\n"

        tables_used = ', '.join(context.get('tables_queried', []))

        prompt = f"""You are a precise data analyst for Team USA Olympic and Paralympic athletes.
The data below was ACTUALLY FETCHED from BigQuery. It is real, complete, and authoritative.
Tables queried this request: {tables_used}

{history_section}
QUESTION: {question}

═══ OLYMPIC DATA ═══
Total Olympic athletes: {oly.get('total_athletes', 0)}
Olympic sports (name: total US athletes): {sports_text}
Top 15 Olympic hometowns (ranked by total athletes):
{hometowns_text}
{extra}
{para_section}
═══ RULES ═══
1. The data above IS available — answer directly with exact numbers. Never say "data is not available" if numbers appear above.
2. If a specific year is marked with *** above, report that number directly (e.g., "In 1988, there were 7 tennis athletes").
3. Resolve conversation history references: "it", "they", "that sport" → use prior context.
4. Use geographic context (elevation, climate, region) to explain patterns when relevant.
5. If a value truly has NO DATA (marked with "*** NOTE: ... has NO data ***"), state which table was checked.
6. Bullet points or numbered lists for multi-item answers.
7. Under 300 words unless more detail is clearly needed.
8. Do NOT invent numbers not present in the data above.

Answer:"""

        try:
            response = self.model.generate_content(prompt, generation_config=_GENERATION_CONFIG)
            return response.text.strip()
        except Exception as e:
            return f"I encountered an error analyzing the data: {str(e)}"
