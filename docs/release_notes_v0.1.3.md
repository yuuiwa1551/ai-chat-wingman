# AI Chat Wingman v0.1.3

Windows preview patch focused on code-review fixes, long-running tasks, and local data control.

## What's Updated

1. Screenshot parsing now runs through the `jobs` table: the endpoint returns a `job_id` and the client polls for the result, so slow multimodal calls no longer block the HTTP request.
2. Target organization also runs through a background job with progress polling and cancel-on-unmount handling on the frontend.
3. Added one-click data purge (`POST /privacy/purge`) gated by an explicit confirmation (`confirm_text = DELETE`); business tables and local screenshot/import/backup directories are cleared while Provider config and seeded style presets are preserved by default.
4. The data panel exposes the purge action with a second confirmation input and an optional toggle to also clear Provider settings.
5. Deleting a target now cascades to its conversations, memories, and saved replies instead of leaving orphan rows.
6. Memory extraction, SSE reading, and app bootstrap now degrade gracefully and log warnings instead of silently swallowing errors.

## Boundaries

1. The app still does not automatically read chat apps.
2. The app still does not automatically send messages.
3. API keys are stored through local settings or environment variables, not in the repository.
4. Imported files and generated local data stay under the configured AI Chat Wingman data directory.

## Validation

1. Backend tests pass (`uv run python -m pytest -q`, 18 passed), including a new purge confirmation-gate test.
2. Frontend build verifies the UI compiles (`tsc --noEmit && vite build`).
