RESEARCH_PROMPT_TEMPLATE = """Generate exactly {topics_count} YouTube Shorts topic ideas for a faceless vertical video channel 
focused on the following content category: "{niche}"

TARGET AUDIENCE: Adults aged 18-45 who love history, ancient civilisations, mythology, mysteries, horror, and urban legends.

MANDATORY QUALITY RULES:
1. Every topic MUST create a strong curiosity gap — something that makes a viewer watch the first 3 seconds of a Short.
2. Every topic MUST trigger at least one emotion: shock, wonder, fear, mystery, awe, or horror.
3. Every topic must have a single clear Hook and a single clear Twist/Payoff that fits in a 30-45 second video.
4. Topics that are too generic or academic will be penalised. Score them below 70.
5. REJECT these patterns: "History of X", "Overview of Y", "Introduction to Z", "The Roman Empire", "Ancient Egypt".
6. EVERY topic idea must feel like a mind-blowing or terrifying fact.

SCORING CRITERIA (0-100):
- Curiosity gap/Hook strength: 30 points
- Payoff/Twist emotional impact: 30 points  
- Virality & shareability: 25 points
- Retention potential: 15 points

GOOD TOPIC EXAMPLES (use as inspiration, do NOT copy):
- "The Emperor Who Declared War on the Sea"
- "The God Even Zeus Feared"
- "The Village That Vanished Overnight"
- "The Real Story Behind the Annabelle Doll"
- "The King Who Accidentally Ate Gold"
- "The Most Terrifying Japanese Legend Ever Told"

BAD TOPIC EXAMPLES (never generate these):
- "History of Rome"
- "Greek Mythology Overview"  
- "The Roman Empire"
- "Introduction to Mythology"

Return JSON only. Do not wrap in backticks or code blocks. Return a single JSON object.

The JSON object MUST have the following structure:
{{
  "topics": [
    {{
      "topic": "Specific, curiosity-driven, emotionally-charged Shorts title",
      "score": 95,
      "audience": "Description of who would watch this Short",
      "keywords": ["keyword1", "keyword2", "keyword3"],
      "reasoning": "Why this Short topic will perform well: hook, twist, retention potential"
    }}
  ]
}}
"""
