# AI Chat Wingman v0.1.2

Windows preview patch focused on first-run readiness and desktop usability.

## What's Updated

1. First-run flow now starts with real OpenAI-compatible Provider setup. Users must enter API URL, API Key, model name, and pass connectivity testing before continuing.
2. Import is now mandatory for new users. QQ JSON import comes before the main workspace, and there is no skip path into normal use.
3. The desktop window opens larger, is no longer always-on-top by default, and exposes explicit pin/minimize controls.
4. The app shell removes the internal frame feel and prevents page-level horizontal scrolling.
5. `start_app.bat` starts the desktop app in a quieter background mode instead of leaving multiple terminal windows in front of users.
6. Workspace navigation exposes the existing import, history, style calibration, and data panels.
7. Version metadata and tag-release notes are aligned for the v0.1.2 build path.

## Boundaries

1. The app still does not automatically read chat apps.
2. The app still does not automatically send messages.
3. API keys are stored through local settings or environment variables, not in the repository.
4. Imported files and generated local data stay under the configured AI Chat Wingman data directory.

## Validation

1. Backend tests cover local API startup and Vite CORS.
2. Frontend build verifies the first-run and workspace UI compile.
3. Manual flow checks cover provider setup, mandatory import, main workspace entry, and reply generation.
