import os
import sys
import time
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ollama_service import OllamaService
from config.settings import settings
from prompts.system_prompts import SYSTEM_RESEARCH_AGENT, SYSTEM_SCRIPT_AGENT
from prompts.research_prompts import RESEARCH_PROMPT_TEMPLATE
from prompts.script_prompts import SCRIPT_PROMPT_TEMPLATE

sys.stdout.reconfigure(encoding='utf-8')

ollama = OllamaService()
model_name = settings.OLLAMA_MODEL
print(f"Starting Ollama Speed Benchmark for model '{model_name}'...")

results = {}

# Test A
print("\n--- Test A: Prompt 'Hello' ---")
start = time.time()
res_a = ollama.generate(prompt="Hello", model=model_name, json_mode=False)
elapsed_a = time.time() - start
print(f"Elapsed: {elapsed_a:.2f}s. Response: {res_a.strip()}")
results["test_a"] = {
    "prompt": "Hello",
    "elapsed_seconds": round(elapsed_a, 2),
    "response_length_chars": len(res_a),
    "response": res_a.strip()
}

# Test B
print("\n--- Test B: Prompt 'Generate 3 history topics.' ---")
start = time.time()
res_b = ollama.generate(prompt="Generate 3 history topics.", model=model_name, json_mode=False)
elapsed_b = time.time() - start
print(f"Elapsed: {elapsed_b:.2f}s. Response: {res_b.strip()[:100]}...")
results["test_b"] = {
    "prompt": "Generate 3 history topics.",
    "elapsed_seconds": round(elapsed_b, 2),
    "response_length_chars": len(res_b),
    "response": res_b.strip()
}

# Test C
print("\n--- Test C: Prompt 'Generate 10 history topics. Return JSON only.' (JSON Mode) ---")
prompt_c = "Generate 10 history topics. Return JSON only."
start = time.time()
res_c = ollama.generate(prompt=prompt_c, model=model_name, json_mode=True)
elapsed_c = time.time() - start
print(f"Elapsed: {elapsed_c:.2f}s. Response length: {len(res_c)}")
results["test_c"] = {
    "prompt": prompt_c,
    "elapsed_seconds": round(elapsed_c, 2),
    "response_length_chars": len(res_c),
    "response": res_c.strip()
}

# Test D
print("\n--- Test D: Actual ResearchAgent prompt ---")
prompt_d = RESEARCH_PROMPT_TEMPLATE.format(
    niche="The Darkest Emperors and Rulers Who Terrorised the Ancient World",
    topics_count=settings.CONTENT_TOPICS_COUNT
)
start = time.time()
res_d = ollama.generate(prompt=prompt_d, system_prompt=SYSTEM_RESEARCH_AGENT, model=model_name, json_mode=True)
elapsed_d = time.time() - start
print(f"Elapsed: {elapsed_d:.2f}s. Response length: {len(res_d)}")
results["test_d"] = {
    "prompt_length_chars": len(prompt_d),
    "elapsed_seconds": round(elapsed_d, 2),
    "response_length_chars": len(res_d),
    "response": res_d.strip()
}

# Test E
print("\n--- Test E: Actual ScriptAgent prompt ---")
prompt_e = SCRIPT_PROMPT_TEMPLATE.format(
    topic="The Emperor Who Ordered His Own People to Kill Him",
    min_words=settings.CONTENT_SCRIPT_MIN_WORDS,
    max_words=settings.CONTENT_SCRIPT_MAX_WORDS
)
start = time.time()
res_e = ollama.generate(prompt=prompt_e, system_prompt=SYSTEM_SCRIPT_AGENT, model=model_name, json_mode=True)
elapsed_e = time.time() - start
print(f"Elapsed: {elapsed_e:.2f}s. Response length: {len(res_e)}")
results["test_e"] = {
    "prompt_length_chars": len(prompt_e),
    "elapsed_seconds": round(elapsed_e, 2),
    "response_length_chars": len(res_e),
    "response": res_e.strip()
}

os.makedirs("generated/reports", exist_ok=True)
report_path = "generated/reports/ollama_benchmark.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nAll tests completed! Report saved to {report_path}")
