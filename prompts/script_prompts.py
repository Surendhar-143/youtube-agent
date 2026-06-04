SCRIPT_PROMPT_TEMPLATE = """Write a gripping, fast-paced YouTube Shorts script for the following topic:

TOPIC: "{topic}"

CHANNEL STYLE: Viral vertical video storytelling — think high-impact, fast narration, no fluff, immediately hooks the viewer.
AUDIENCE: Adults aged 18-45 who love history, mythology, mysteries, and horror.
TONE: Dramatic, suspenseful, punchy.
LENGTH: Between {min_words} and {max_words} words (strictly enforced). Do NOT exceed 200 words under any circumstances.

INSTRUCTIONS:
1. Start directly with the hook. Do NOT say "In today's video" or "Welcome back".
2. Hook must be the first 1-2 sentences (0-5 seconds) and be extremely shocking.
3. Keep the narration flowing, fast-paced, and concise. Use simple, high-impact words.
4. Conclude with a strong twist or reveal and a punchy 1-sentence Call to Action.

CRITICAL JSON FORMATTING RULES:
1. The 'script' key MUST map to a single string value.
2. The entire narration text MUST be one continuous string, with paragraphs separated by \\n\\n.
3. Ensure all double quotes inside the strings are escaped (\\").

Return JSON only. Just a raw JSON object:
{{
  "title": "Short, curiosity-driven title (under 100 characters)",
  "hook": "The first 5 seconds hook sentence(s)",
  "script": "Shocking hook sentence...\\n\\nFast-paced story details...\\n\\nTwist/reveal payoff...\\n\\nQuick CTA close.",
  "estimated_seconds": 45,
  "word_count": 100
}}
"""
