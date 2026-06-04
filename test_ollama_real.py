import sys
import os
import time

sys.path.append(r"c:\Users\Surendhar\OneDrive\Desktop\youtube_agent")

from prompts.system_prompts import SYSTEM_RESEARCH_AGENT
from prompts.research_prompts import RESEARCH_PROMPT_TEMPLATE
from services.ollama_service import OllamaService
from config.settings import settings

sys.stdout.reconfigure(encoding='utf-8')

ollama = OllamaService()
prompt = RESEARCH_PROMPT_TEMPLATE.format(
    niche="The Darkest Emperors and Rulers Who Terrorised the Ancient World", 
    topics_count=settings.CONTENT_TOPICS_COUNT
)

def run_test(model_name, json_mode):
    print(f"\n--- Testing {model_name} with json_mode={json_mode} ---")
    start = time.time()
    try:
        res = ollama.generate(
            prompt=prompt,
            system_prompt=SYSTEM_RESEARCH_AGENT,
            model=model_name,
            json_mode=json_mode
        )
        elapsed = time.time() - start
        print(f"Completed in {elapsed:.2f}s!")
        print("Response length:", len(res))
        print("Response text:")
        print(res)
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed in {elapsed:.2f}s with error: {e}")

run_test("qwen2.5:7b", json_mode=True)
