# AI Chat Wingman v0.1.4

Windows preview patch focused on async consistency and local secret safety.

## What's Updated

1. Style calibration analysis now runs through the `jobs` table: `POST /style-test/sessions/{id}/analysis` returns a `job_id` and the client polls for the result, so slow analysis no longer blocks the HTTP request. This completes moving every long LLM task off the synchronous request path.
2. The style test panel shows analysis progress and stops polling when the view unmounts.
3. Provider API keys are now encrypted at rest. Keys are stored as `enc:v1:` ciphertext in the local database, protected by a per-install random key file (`secret.key`, restricted permissions) under the app data directory.
4. Legacy clear-text keys keep working and are upgraded to ciphertext the next time the provider is saved.
5. One-click purge with `include_settings` now also removes the local secret key file so no orphan key remains.

## Boundaries

1. The app still does not automatically read chat apps.
2. The app still does not automatically send messages.
3. API keys are stored encrypted through local settings, never in the repository.
4. Imported files and generated local data stay under the configured AI Chat Wingman data directory.

## Validation

1. Backend tests pass (`uv run python -m pytest -q`, 19 passed), including a secret encryption round-trip / legacy plain-text test and the job-polling style analysis flow.
2. Frontend build verifies the UI compiles (`tsc --noEmit && vite build`).
