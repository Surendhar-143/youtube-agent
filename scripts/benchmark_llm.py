import sys
import os
import json
import time
import argparse
from typing import Dict, Any
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from services.gemini_service import GeminiService
from services.ollama_service import OllamaService
from prompts.system_prompts import (
    SYSTEM_RESEARCH_AGENT,
    SYSTEM_SCRIPT_AGENT,
    SYSTEM_SEO_AGENT,
    SYSTEM_SCENE_AGENT
)
from prompts.research_prompts import RESEARCH_PROMPT_TEMPLATE
from prompts.script_prompts import SCRIPT_PROMPT_TEMPLATE
from prompts.seo_prompts import SEO_PROMPT_TEMPLATE
from prompts.scene_prompts import SCENE_PROMPT_TEMPLATE

def run_task(provider: Any, provider_name: str, task_name: str, prompt: str, system_prompt: str, is_json: bool = True) -> Dict[str, Any]:
    print(f"[{provider_name}] Running {task_name}...")
    start_time = time.time()
    success = False
    error = None
    response_length = 0
    json_valid = False
    
    try:
        if is_json:
            # We want to use generate with json_mode=True to test actual generation length and parsing manually
            # But GeminiService has generate_json. Ollama has generate(json_mode=True).
            # We'll use the raw generate method with json_mode=True to get raw text for length measurement.
            response_text = provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                json_mode=True
            )
            response_length = len(response_text)
            
            # Clean markdown code block if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            try:
                json.loads(text.strip())
                json_valid = True
                success = True
            except json.JSONDecodeError as e:
                json_valid = False
                success = False
                error = f"JSON parsing failed: {str(e)}"
        else:
            response_text = provider.generate(prompt=prompt, system_prompt=system_prompt)
            response_length = len(response_text)
            success = True
            
    except Exception as e:
        success = False
        error = str(e)
        
    duration = time.time() - start_time
    
    return {
        "task": task_name,
        "latency": duration,
        "response_length": response_length,
        "success": success,
        "json_valid": json_valid if is_json else None,
        "error": error
    }

def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM Providers")
    parser.add_argument("--providers", nargs="+", default=["gemini", "ollama"], help="Providers to benchmark")
    args = parser.parse_args()
    
    print("Starting LLM Benchmark Suite...")
    os.makedirs("generated/reports", exist_ok=True)
    report_file = "generated/reports/llm_benchmark.json"
    
    report = {
        "timestamp": time.time(),
        "providers": {}
    }
    
    providers = {}
    if "gemini" in args.providers:
        try:
            providers["gemini"] = GeminiService()
        except Exception as e:
            print(f"Failed to init GeminiService: {e}")
            
    if "ollama" in args.providers:
        providers["ollama"] = OllamaService()

    # Define tasks
    niche = "ancient Rome"
    research_prompt = RESEARCH_PROMPT_TEMPLATE.format(niche=niche, topics_count=2)
    
    topic = "The Fall of the Roman Empire"
    script_prompt = SCRIPT_PROMPT_TEMPLATE.format(topic=topic, min_words=100, max_words=200)
    
    script_text = "The Roman Empire was one of the largest and most powerful empires in history. It began in Rome..."
    seo_prompt = SEO_PROMPT_TEMPLATE.format(
        title=topic,
        script=script_text,
        title_max_len=100,
        description_max_len=5000,
        min_tags=15,
        min_hashtags=10
    )
    
    scene_prompt = SCENE_PROMPT_TEMPLATE.format(
        title=topic,
        script=script_text,
        words_per_second=2.5
    )
    
    tasks = [
        ("Research", research_prompt, SYSTEM_RESEARCH_AGENT),
        ("Script", script_prompt, SYSTEM_SCRIPT_AGENT),
        ("SEO", seo_prompt, SYSTEM_SEO_AGENT),
        ("Scene", scene_prompt, SYSTEM_SCENE_AGENT)
    ]
    
    for provider_name, provider_inst in providers.items():
        provider_report = []
        for task_name, prompt, sys_prompt in tasks:
            result = run_task(provider_inst, provider_name, task_name, prompt, sys_prompt)
            provider_report.append(result)
            print(f"  -> Success: {result['success']}, Latency: {result['latency']:.2f}s")
            
        report["providers"][provider_name] = provider_report

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nBenchmark complete. Report saved to {report_file}")

if __name__ == "__main__":
    main()
