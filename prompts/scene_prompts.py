SCENE_PROMPT_TEMPLATE = """Break down the following Shorts script into a sequence of cinematic visual scenes for a vertical 1080x1920 video.

Script Title: {title}
Complete Script Content:
{script}

CHANNEL STYLE: Cinematic vertical video (Shorts/TikTok) — fast-paced, high retention. Every scene must be highly visual, dynamic, and match a 9:16 aspect ratio.

SCENE COUNT REQUIREMENT:
- For a Short of this length, you MUST generate between 3 and 8 scenes.
- Typical structure:
  - Scene 1: The Hook (extreme visual to capture attention)
  - Scene 2-4: The Story details (different dynamic visual types)
  - Scene 5: The Twist or Reveal (shocking payoff visual)
  - Scene 6: The Call to Action (clean, engaging final frame)

AVAILABLE VISUAL TYPES (choose the most appropriate):
- BROLL: Generic atmospheric footage — landscapes, skies, dark rooms, mysterious visuals.
- HISTORICAL_PAINTING: Classical paintings or illustrations.
- ANCIENT_MAP: Ancient maps, routes, or layouts.
- ARTIFACT: Ancient relics, coins, weapons, books.
- AERIAL: Aerial view of landscapes or ruins.
- REENACTMENT: Reenactors, actors in period costumes, dramatic action.
- TEXT_OVERLAY: Shocking text on screen (e.g. key quotes, statistics, dates).
- ANIMATION: Simple motion graphics.

VISUAL VARIETY RULES:
- NEVER use the same visual_type for consecutive scenes.
- Pacing must be fast. Keep scene durations short (typically 3–8 seconds per scene).

FOR EACH SCENE, PROVIDE:
1. scene_number: Sequential integer starting from 1.
2. title: Short cinematic title.
3. description: Detailed vertical cinematography instructions (camera angle, focus, lighting, mood).
4. narration_text: The EXACT script text spoken during this visual.
5. estimated_duration: Scene duration in seconds. Assume {words_per_second} words per second of narration.
6. visual_type: Choose ONE from the list above.
7. keywords: 3–5 specific search terms for vertical stock footage.

RESPONSE FORMAT — raw JSON only, matching this structure exactly:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene Title",
      "description": "Detailed vertical framing/visual description...",
      "narration_text": "Exact script text for this scene...",
      "estimated_duration": 5.0,
      "visual_type": "BROLL",
      "keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ]
}}
"""
