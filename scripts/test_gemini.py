import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gemini_service import GeminiService
from config.settings import settings

def main():
    print("Starting Gemini Service tests...")
    
    # Ensure reports directory exists
    os.makedirs("generated/reports", exist_ok=True)
    report_file = "generated/reports/gemini_test_report.json"
    
    report = {
        "timestamp": time.time(),
        "provider": settings.LLM_PROVIDER,
        "model": settings.GEMINI_MODEL,
        "tests": []
    }
    
    service = GeminiService()
    
    # Test 1: Connection (health_check)
    print("\n--- Test 1: Connection ---")
    start = time.time()
    try:
        health = service.health_check()
        duration = time.time() - start
        success = health.get("connected", False)
        print(f"Health Check: {'PASS' if success else 'FAIL'} (Latency: {health.get('latency', 0):.4f}s)")
        report["tests"].append({
            "name": "connection",
            "success": success,
            "duration": duration,
            "details": health
        })
    except Exception as e:
        print(f"Connection test failed: {e}")
        report["tests"].append({
            "name": "connection",
            "success": False,
            "error": str(e)
        })

    # Test 2: Simple prompt
    print("\n--- Test 2: Simple Prompt ---")
    start = time.time()
    try:
        response = service.generate(prompt="Hello", max_tokens=10)
        duration = time.time() - start
        success = bool(response and len(response) > 0)
        print(f"Response: {response}")
        print(f"Simple Prompt: {'PASS' if success else 'FAIL'} (Duration: {duration:.4f}s)")
        report["tests"].append({
            "name": "simple_prompt",
            "success": success,
            "duration": duration,
            "response": response
        })
    except Exception as e:
        print(f"Simple prompt failed: {e}")
        report["tests"].append({
            "name": "simple_prompt",
            "success": False,
            "error": str(e)
        })

    # Test 3: History topics
    print("\n--- Test 3: History Topics ---")
    start = time.time()
    try:
        prompt = "Generate 5 history video ideas."
        response = service.generate(prompt=prompt)
        duration = time.time() - start
        success = bool(response and len(response) > 50)
        print(f"Response length: {len(response)} chars")
        print(f"History Topics: {'PASS' if success else 'FAIL'} (Duration: {duration:.4f}s)")
        report["tests"].append({
            "name": "history_topics",
            "success": success,
            "duration": duration,
            "response_length": len(response)
        })
    except Exception as e:
        print(f"History topics failed: {e}")
        report["tests"].append({
            "name": "history_topics",
            "success": False,
            "error": str(e)
        })

    # Test 4: JSON generation
    print("\n--- Test 4: JSON Generation ---")
    start = time.time()
    try:
        prompt = "Return exactly this JSON: {\"title\": \"Ancient Rome\", \"score\": 9}"
        result = service.generate_json(prompt=prompt)
        duration = time.time() - start
        success = isinstance(result, dict) and result.get("score") == 9
        print(f"Parsed JSON: {result}")
        print(f"JSON Generation: {'PASS' if success else 'FAIL'} (Duration: {duration:.4f}s)")
        report["tests"].append({
            "name": "json_generation",
            "success": success,
            "duration": duration,
            "parsed_json": result
        })
    except Exception as e:
        print(f"JSON generation failed: {e}")
        report["tests"].append({
            "name": "json_generation",
            "success": False,
            "error": str(e)
        })

    # Save report
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nTests complete. Report saved to {report_file}")
    
    if all(t.get("success", False) for t in report["tests"]):
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
