"""Adversarial/Failure Handling Verification Script."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import json

API_URL = "http://127.0.0.1:8000/api/compile"

def test_prompt(name, prompt):
    print(f"\n--- Testing: {name} ---")
    print(f"Prompt: \"{prompt}\"")
    
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"prompt": prompt}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode("utf-8"))
        
        print(f"Compilation Success: {data.get('success')}")
        if not data.get("success"):
            print(f"Error Message: \"{data.get('error')}\"")
            stages = data.get("pipeline", {}).get("stages", [])
            if stages:
                print(f"Failed Stage: {stages[0]['stage']}")
                print(f"Validation Errors Count: {stages[0]['validation_errors']}")
                errors = stages[0].get("errors", [])
                if errors:
                    print(f"First Error Detail: {errors[0].get('message')}")
        else:
            print("❌ Expected compilation failure, but it succeeded!")
            
    except Exception as e:
        print(f"CRASH: {e}")

if __name__ == "__main__":
    # Test Case 1: Vague Prompt
    test_prompt("Vague Prompt (Build a Website)", "Build a Website")
    
    # Test Case 2: Authentication Contradiction
    test_prompt(
        "Contradiction (No Auth but Logged User Access)",
        "build without authentication but logged use accesed"
    )
    
    # Test Case 3: Public vs Private Contradiction
    test_prompt(
        "Private vs Public Conflict",
        "Build an app where all posts are private and only visible to the author, but also include a public feed where everyone can see all posts."
    )
