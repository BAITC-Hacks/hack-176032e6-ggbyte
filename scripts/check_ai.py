"""Test an API on independently authored examples only; never loads data/ or SQLite."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from career.ai import load_env, configuration, anonymous_context, request_model
from career.engine import recommend
from examples.demo import dataset

load_env(Path(__file__).resolve().parents[1])
config = configuration()
if config['provider'] not in ('openai', 'nvidia', 'ollama'):
    raise SystemExit('Configure an AI provider in .env first.')
fixtures = dataset()
result = recommend(fixtures['employees']['employees'][0], fixtures['history'],
                   {e['event_id']: e for e in fixtures['events']['events']},
                   {s['skill_id']: s for s in fixtures['skills']['skills']},
                   fixtures['skills']['role_profiles'], '2026-10-01')
mapping, context = anonymous_context(result)
print('Source: independent repository examples; no organizer data is read.', flush=True)
import time
started = time.monotonic()
try:
    selected = request_model(config, context)
    if not isinstance(selected, list) or not 1 <= len(selected) <= 3 or any(e not in mapping for e in selected):
        raise ValueError('Invalid candidate selection')
    if mapping[selected[0]] != 'DEMO_DESIGN':
        raise ValueError('Critical System Design must be prioritized in this example')
    print(f"PASS: {config['provider']} / {config['model']}; critical skill prioritized; {time.monotonic() - started:.2f} seconds.")
except Exception as error:
    # Do not print request headers, keys, or provider response bodies.
    print(f'FAIL: {type(error).__name__}; HTTP status: {getattr(error, "code", "n/a")}. Check key, model and connection.')
    raise SystemExit(1)
