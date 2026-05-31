# AI Chat Wingman v0.1.5

Windows preview patch focused on front-end job-polling consistency and clearer privacy feedback.

## What's Updated

1. Added a shared `useCancellableJob` hook that centralizes job-polling lifecycle (cancel on unmount, progress callback). Five panels now reuse it instead of duplicating `useRef`/`useEffect` boilerplate: QQ import, image input, target organize, style test, and data backup.
2. The data backup flow now goes through the shared `pollJobResult` helper instead of a hand-rolled local polling loop, so backup progress and cancellation behave the same as every other long task.
3. One-click purge now shows an itemized report after completion: how many rows were deleted per table, how many local files were removed, and whether Provider settings were included.

## Boundaries

1. The app still does not automatically read chat apps.
2. The app still does not automatically send messages.
3. API keys remain encrypted at rest through local settings, never in the repository.
4. Imported files and generated local data stay under the configured AI Chat Wingman data directory.

## Validation

1. Backend tests pass (`uv run python -m pytest -q`, 19 passed).
2. Frontend build verifies the UI compiles (`tsc --noEmit && vite build`).
