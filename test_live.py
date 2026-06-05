"""Live end-to-end test — sends a real prompt through the full pipeline."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import urllib.request

API_URL = "http://127.0.0.1:8000/api/compile"

prompt = (
    "Build a CRM with login, contacts management, deal pipeline, "
    "dashboard with analytics, role-based access for admin and sales reps, "
    "and premium plan with payments. Admins can see all analytics "
    "while sales reps only see their own deals."
)

print("=" * 60)
print("LIVE END-TO-END TEST")
print("=" * 60)
print(f"Prompt: {prompt[:80]}...")
print("Sending to pipeline...\n")

req = urllib.request.Request(
    API_URL,
    data=json.dumps({"prompt": prompt}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    response = urllib.request.urlopen(req, timeout=120)
    data = json.loads(response.read().decode("utf-8"))

    print(f"Success: {data.get('success')}")
    print()

    if data.get("success"):
        spec = data.get("app_spec", {})
        meta = spec.get("metadata", {})
        print(f"App Name: {meta.get('name', '?')}")
        print(f"UI Pages: {len(spec.get('ui', {}).get('pages', []))}")
        print(f"API Endpoints: {len(spec.get('api', {}).get('endpoints', []))}")
        print(f"DB Tables: {len(spec.get('db', {}).get('tables', []))}")
        print(f"Auth Roles: {len(spec.get('auth', {}).get('roles', []))}")
        print(f"Business Rules: {len(spec.get('business_logic', []))}")

        # Pipeline info
        pipeline = data.get("pipeline", {})
        print(f"\nPipeline Latency: {pipeline.get('total_latency_ms', 0) / 1000:.1f}s")
        for stage in pipeline.get("stages", []):
            status = "PASS" if stage["success"] else "FAIL"
            print(f"  {stage['stage']}: {status} ({stage['latency_ms']/1000:.1f}s, {stage['repair_attempts']} repairs)")

        # Cost info
        cost = data.get("cost", {})
        print(f"\nCost: ${cost.get('total_cost_usd', 0):.4f}")
        print(f"Tokens: {cost.get('total_tokens', 0)}")
        print(f"LLM Calls: {cost.get('total_calls', 0)} ({cost.get('repair_calls', 0)} repairs)")

        # Runtime info
        runtime = data.get("runtime", {})
        if runtime:
            print(f"\nRuntime Executable: {runtime.get('is_executable', False)}")
            print(f"Checks: {runtime.get('checks_passed', 0)} passed, {runtime.get('checks_failed', 0)} failed")

        # Save full output
        with open("test_output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("\nFull output saved to test_output.json")

        print("\n" + "=" * 60)
        print("END-TO-END TEST PASSED!")
        print("=" * 60)
    else:
        print(f"Error: {data.get('error', 'Unknown')}")
        print("\nPipeline stages:")
        for stage in data.get("pipeline", {}).get("stages", []):
            status = "PASS" if stage["success"] else "FAIL"
            print(f"  {stage['stage']}: {status}")

except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"HTTP Error {e.code}: {body}")
except Exception as e:
    print(f"Error: {e}")
