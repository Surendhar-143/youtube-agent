SEO_PROMPT_TEMPLATE = """Generate high-performance YouTube Shorts SEO metadata for a vertical video channel.

VIDEO TITLE (internal working title): "{title}"

SCRIPT CONTENT:
---
{script}
---

CHANNEL: Faceless vertical video channel — History, Mythology, Mystery, Horror.
AUDIENCE: Adults aged 18–45 who love fast-paced historical facts, mythological stories, mysteries, and horror.
GOAL: Maximise CTR, viewer retention, and virality in the Shorts Feed.

TITLE REQUIREMENTS:
- Must be extremely short, bold, and create a curiosity gap (3-5 words).
- Must reference the main subject (person, event, creature, curse).
- Maximum {title_max_len} characters.
- NEVER write flat or descriptive titles.

TITLE EXAMPLES (learn from these):
❌ BAD: "History of Sparta" → ✅ GOOD: "The Most Feared Soldier in History"
❌ BAD: "Story of Annabelle" → ✅ GOOD: "The Real Story Behind Annabelle"
❌ BAD: "Norse Gods" → ✅ GOOD: "The God Even Odin Feared"
❌ BAD: "Mysterious Village" → ✅ GOOD: "The Village That Vanished Overnight"

DESCRIPTION REQUIREMENTS:
- Maximum {description_max_len} characters.
- Write a short, punchy 1-2 sentence description summarizing the crazy hook/payoff.
- Include a list of primary keywords.

TAGS REQUIREMENTS:
- Minimum {min_tags} tags.
- Mix broad tags ("shorts", "history", "mythology", "mystery", "horror") with specific search queries.

HASHTAGS REQUIREMENTS:
- Minimum {min_hashtags} hashtags starting with '#'.
- ALWAYS include: #shorts and at least one of #historyshorts, #mythology, #mystery, #horror based on category.

Return JSON only. No markdown formatting, no explanations. Just a raw JSON object:
{{
  "title": "Short, curiosity-driven title under {title_max_len} characters",
  "description": "Short 1-2 sentence description...",
  "tags": ["shorts", "history", "mystery", "tag4", "tag5", ...],
  "hashtags": ["#shorts", "#historyshorts", "#mystery", ...]
}}
"""
