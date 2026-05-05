import google.generativeai as genai
from config import Config

class GeminiHandler:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        self.story_cache = {}
        print("✅ GeminiHandler initialized with cache")

    def generate_hometown_story(self, hometown_data, mode='olympic'):
        import pandas as pd

        # Cache check — key includes mode since Olympic/Paralympic stories differ
        hometown_id = hometown_data.get('hometown_id')
        cache_key = f"{hometown_id}_{mode}" if hometown_id else None
        if cache_key and cache_key in self.story_cache:
            print(f"✅ Cache HIT: {hometown_id} ({mode})")
            return self.story_cache[cache_key]
        print(f"🔄 Cache MISS: {hometown_id} ({mode}) - generating new story")

        label = 'Paralympic' if mode == 'paralympic' else 'Olympic'

        city_name     = hometown_data.get('city_name', 'Unknown')
        state_code    = hometown_data.get('state_code', 'Unknown')
        total_athletes = hometown_data.get('total_athletes', 0)
        top_sports    = hometown_data.get('top_sports', [])

        region            = hometown_data.get('region', 'Unknown')
        elevation         = hometown_data.get('elevation')
        distance_to_coast = hometown_data.get('distance_to_nearest_coast_km')
        climate_zone      = hometown_data.get('climate_zone', 'Unknown')

        sports_text = ", ".join(
            [f"{s['sport_name']} ({s['count']} athletes)" for s in top_sports[:3]]
        )
        if not sports_text:
            sports_text = "various sports"

        geographic_context = ""

        if elevation and not pd.isna(elevation):
            elevation = float(elevation)
            if elevation > 3000:
                geographic_context += (
                    f"Located at {elevation:.0f} meters above sea level, "
                    "the high altitude may provide training advantages for endurance sports. "
                )
            elif elevation > 1500:
                geographic_context += (
                    f"Situated at {elevation:.0f} meters elevation, "
                    "this elevated terrain could contribute to athletic development. "
                )
            else:
                geographic_context += f"Located at {elevation:.0f} meters, "

        if distance_to_coast and not pd.isna(distance_to_coast):
            distance_to_coast = float(distance_to_coast)
            if distance_to_coast < 50:
                geographic_context += "Being close to the coast may provide access to diverse training environments. "
            elif distance_to_coast < 200:
                geographic_context += (
                    f"Positioned {distance_to_coast:.0f} km from the nearest coast, "
                    "the region could offer varied climate conditions. "
                )
            else:
                geographic_context += (
                    f"Located {distance_to_coast:.0f} km from the nearest coast in the interior, "
                    "the region's continental location may foster year-round training. "
                )

        climate_descriptions = {
            'Alpine':              "alpine climate with cool temperatures",
            'Montane':             "montane climate that may support diverse athletic training",
            'Cold Temperate':      "cold temperate climate with distinct seasons",
            'Temperate':           "temperate climate with moderate temperatures",
            'Subtropical':         "subtropical climate with warm conditions",
            'Tropical/Subtropical':"tropical/subtropical climate with consistent warmth",
        }
        climate_desc = climate_descriptions.get(climate_zone, f"{climate_zone} climate")
        geographic_context += f"The {climate_desc} may contribute to the region's athletic culture."

        prompt = f"""You are an expert on US {label} sports history and geography.

Write an engaging 2-3 paragraph story explaining how {city_name}, {state_code} \
has produced {total_athletes} {label} athletes, primarily in {sports_text}.

This story is about {label.upper()} athletes specifically — not Olympic athletes in general.
{"Acknowledge the unique challenges and achievements of Paralympic athletes where relevant." if label == "Paralympic" else ""}

GEOGRAPHIC AND CLIMATE CONTEXT:
- Region: {region}
- Elevation: {f"{elevation:.0f} meters" if elevation and not pd.isna(elevation) else "Not specified"}
- Climate Zone: {climate_zone}

GUIDELINES:
1. Geographic Factors: Consider elevation, climate
2. Use CONDITIONAL language: "may have", "could suggest", "might indicate"
3. AVOID absolute claims: "guarantees", "proves", "causes"
4. Connect geography to the sports developed
5. Keep it suitable for a public website
6. Write in English only, 2-3 paragraphs, 200-300 words total
7. Be engaging and informative
8. If information is missing, acknowledge uncertainty rather than fabricating details
9. If possible, use bullet points for clarity
10. At the end, provide the total word count in parentheses

Story:"""

        try:
            response = self.model.generate_content(prompt)
            story = response.text
            if cache_key:
                self.story_cache[cache_key] = story
                print(f"✅ Cached: {hometown_id} ({mode})")
            return story
        except Exception as e:
            return f"Failed to generate story: {str(e)}"

    def clear_cache(self):
        count = len(self.story_cache)
        self.story_cache.clear()
        print(f"🗑️ Cache cleared: {count} stories removed")
        return count

    def get_cache_stats(self):
        import sys
        size_bytes = sum(sys.getsizeof(v) for v in self.story_cache.values())
        return {
            'cached_stories': len(self.story_cache),
            'cache_size_bytes': size_bytes,
        }

    def generate_heatmap_description(self, sport_name, top_locations, total_athletes, mode='olympic'):
        label = 'Paralympic' if mode == 'paralympic' else 'Olympic'

        locations_text = '; '.join(
            f"{h.get('city_name') or h.get('state_code', '?')}, {h.get('state_code', '')} ({h.get('sport_athletes', 0)})"
            for h in top_locations[:5]
        )

        prompt = f"""You are a sports geography analyst.

US {label} sport: {sport_name}
Total athletes mapped: {total_athletes}
Top concentrations: {locations_text}

Respond in exactly this format (no other text):
OBSERVATIONS: [1-2 sentences under 45 words about the geographic concentration pattern and one possible reason, specific to the locations]
FACTS: [1 sentence under 25 words: fact-based comment on whether {total_athletes} {label} athletes in {sport_name} is a large or small number, and why it might be so]"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            observations, facts = '', ''
            for line in text.split('\n'):
                line = line.strip()
                if line.upper().startswith('OBSERVATIONS:'):
                    observations = line[len('OBSERVATIONS:'):].strip()
                elif line.upper().startswith('FACTS:'):
                    facts = line[len('FACTS:'):].strip()
            # Fallback: if format not followed, use full text as observations
            if not observations:
                observations = text
            return {'observations': observations, 'facts': facts}
        except Exception:
            return None

    def generate_map_observation(self, top_hometowns, total_athletes, mode='olympic', focus_region=False):
        label = 'Paralympic' if mode == 'paralympic' else 'Olympic'

        locations_text = '; '.join(
            f"{h.get('city_name', '?')}, {h.get('state_code', '')} ({h.get('total_athletes', 0)})"
            for h in top_hometowns[:10]
        )

        focus_instruction = (
            "The description should be focused on the displayed region of the mapview, "
            "i.e. if the map view is displaying the TX area, you should start with something like "
            "'The athlete hometowns in the TX area ...'. "
            if focus_region else ""
        )

        prompt = f"""You are a sports geography analyst examining US {label} athlete hometowns.

Total {label} athletes: {total_athletes}
Top hometowns: {locations_text}

{focus_instruction}Write 1-2 sentences (strictly under 60 words) observing the geographic distribution pattern (coastal vs inland, regional clusters, urban concentration, etc.) and suggesting one possible reason. Be specific about the locations."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return None

    def generate_sport_animation(self, sport_name, mode='olympic'):
        label = 'Paralympic' if mode == 'paralympic' else 'Olympic'

        prompt = f"""You are a very creative cartoon artist. Please generate an interesting cartoon for the provided sport which can demonstrate the key information of this sport.

Sport: "{sport_name}" ({label})

Output ONLY raw SVG markup — no markdown code fences, no explanation, no extra text.
Start with <svg and end with </svg>.

Technical requirements:
- viewBox="0 0 600 260" width="100%" height="100%"
- Static illustration only — no CSS animations or keyframes
- NO JavaScript
- Background should complement the sport (solid color)
- Use simple shapes and bold lines to create a clear, visually appealing cartoon style
- Don't use any logo or trademarked elements from any organization or brand

Visual requirements:
- Create a fun, colorful cartoon illustration that clearly demonstrates the key elements of {sport_name}
- Include cartoon athlete(s), equipment, and environment relevant to the sport
- Use bright, sport-appropriate cartoon colors with bold outlines
- Keep shapes expressive and cartoon-style (rounded forms, thick strokes, exaggerated proportions)
- Show a recognizable sport moment or scene (e.g., a serve, a jump, a finish line)
{"- Use wheelchair or adaptive equipment where appropriate for the Paralympic context" if label == 'Paralympic' else ""}

Output only the raw SVG, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # Strip any markdown code fences Gemini might add
            if '```' in text:
                lines = text.split('\n')
                text = '\n'.join(
                    l for l in lines
                    if not l.strip().startswith('```')
                )
            return text.strip()
        except Exception:
            return None
