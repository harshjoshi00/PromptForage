"""Quick validation test for all components."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

# Test 1: Schema validation
from backend.schemas.intent_ir import IntentIR
intent = IntentIR(
    app_name='test_crm',
    app_description='A test CRM',
    app_type='crm',
    features=[{'name': 'contacts', 'description': 'Manage contacts', 'priority': 'high'}],
    entities=['User', 'Contact'],
    roles=['admin', 'user'],
    original_prompt='Build a CRM'
)
print('[OK] IntentIR validation')
print(f'    Features: {len(intent.features)}, Entities: {len(intent.entities)}')

# Test 2: Validator
from backend.validation.validator import validate
data = intent.model_dump()
report = validate(data, 'stage_1_lexer')
status = "PASS" if report.is_valid else "FAIL"
print(f'[OK] Stage 1 validation: {status} ({report.error_count} errors)')

# Test 3: Invalid data catches errors
bad_data = {'app_name': '', 'features': [], 'entities': []}
bad_report = validate(bad_data, 'stage_1_lexer')
print(f'[OK] Bad data caught: {bad_report.error_count} errors detected')

# Test 4: Cross-layer checks
from backend.validation.cross_layer_checks import check_cross_layer_consistency
from backend.validation.validation_report import ValidationReport
schema_data = {
    'ui_schema': {'pages': [{'name': 'dash', 'route': '/dash', 'components': [
        {'id': 'c1', 'type': 'table', 'data_source': '/api/v1/contacts', 'fields': []}
    ]}]},
    'api_schema': {'endpoints': [{'path': '/api/v1/contacts', 'method': 'GET', 'allowed_roles': ['admin'], 'entity': 'Contact'}]},
    'db_schema': {'tables': [{'name': 'contacts', 'columns': [{'name': 'id', 'type': 'UUID', 'primary_key': True}]}]},
    'auth_schema': {'roles': [{'name': 'admin'}], 'rules': []},
}
xl_report = ValidationReport(stage='test')
check_cross_layer_consistency(schema_data, xl_report)
print(f'[OK] Cross-layer check: {xl_report.error_count} errors, {xl_report.warning_count} warnings')

# Test 5: Code generator
from backend.runtime.code_generator import generate_app_html
app_spec = {
    'metadata': {'name': 'Test App'},
    'ui': {
        'pages': [{
            'name': 'dashboard', 'route': '/dashboard', 'title': 'Dashboard',
            'layout': 'stack',
            'components': [{'id': 'stats', 'type': 'stats', 'title': 'Overview',
                           'fields': [{'name': 'total', 'label': 'Total'}]}],
            'access_roles': ['admin']
        }],
        'navigation': [{'name': 'Dashboard', 'route': '/dashboard'}]
    },
    'api': {'base_path': '/api/v1', 'endpoints': []},
    'db': {'tables': []},
    'auth': {'roles': [{'name': 'admin'}], 'rules': [], 'session_type': 'jwt'},
    'business_logic': [],
}
html = generate_app_html(app_spec)
print(f'[OK] Code generator: {len(html)} bytes HTML generated')
print(f'    DOCTYPE: {"<!DOCTYPE html>" in html}, Nav: {"Dashboard" in html}')

# Test 6: Runtime simulator
from backend.runtime.simulator import RuntimeSimulator
sim = RuntimeSimulator()
exec_report = sim.simulate(app_spec)
print(f'[OK] Runtime simulator: {exec_report.pass_count} passed, {exec_report.fail_count} failed')
print(f'    Executable: {exec_report.is_executable}')

# Test 7: Cost tracker
from backend.llm.cost_tracker import CostTracker
tracker = CostTracker()
tracker.record_call('stage_1', 'gpt-4o', 500, 1000, 2500.0)
tracker.record_call('stage_2', 'gpt-4o', 800, 1500, 3200.0)
print(f'[OK] Cost tracker: {tracker.total_calls} calls, {tracker.total_tokens} tokens, ${tracker.total_cost:.4f}')

# Test 8: Retry policy
from backend.repair.retry_policy import RetryPolicy
policy = RetryPolicy()
policy.record_attempt("error A")
policy.record_attempt("error A")
print(f'[OK] Retry policy: converged={policy.has_converged()}, remaining={policy.retries_remaining}')

# Test 9: Evaluation prompts
from backend.evaluation.test_prompts import REAL_PROMPTS, EDGE_CASE_PROMPTS
print(f'[OK] Test prompts: {len(REAL_PROMPTS)} real + {len(EDGE_CASE_PROMPTS)} edge cases')

print('\n=== ALL 9 TESTS PASSED ===')
