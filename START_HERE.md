# NEXUS — START HERE

**SIH26152 — Social Media Analytics**  
Narrative & Influence Intelligence workspace with evidence-aware social analytics.

## 1. Run the project

From the repository root on Windows:

```bat
copy .env.example .env
scripts\start_demo.bat
```

Then open:

```text
http://127.0.0.1:5173
```

`start_demo.bat` runs the project pre-flight before launching the verified demo build.

## 2. Recommended first demo

1. Search a topic such as `RiverLink`.
2. Click **Fresh Search**.
3. Open **Posts / Explorer**.
4. Use the platform chips to isolate Telegram, YouTube, X, Bluesky, etc.
5. Use **LIVE / REPLAY / IMPORT** filters to show evidence provenance.
6. Open **Trends** → choose a narrative → inspect **Narrative lineage**.
7. Open **Network** for observed high-reach / bridge-node structure.
8. Open **Evidence** to trace individual source events.

## 3. Telegram controlled demo

The project includes `NexusSIHDemo` as a safe demo fallback channel. You can override it locally in `.env`:

```env
TELEGRAM_PUBLIC_CHANNELS=NexusSIHDemo
```

Do not commit bot tokens or API credentials.

## 4. Interface controls

- **Light mode is default**.
- Use the top-right **Theme** control for dark mode.
- Press **Ctrl+K** (or **Cmd+K**) to focus the global search box.
- Use **Connections** for official connector readiness and fallbacks.
- Use **Free Sources** for zero-key/public collection paths.
- The Overview page warns when evidence is limited to a single platform.

## 5. Verify before presenting

Run:

```bat
.\.venv\Scripts\python.exe .\scripts\preflight.py
```

You want:

```text
PRE-FLIGHT PASSED
```

Maven is optional unless using the Spring gateway.

## 6. Create a clean submission ZIP

Run:

```bat
scripts\export_submission.bat
```

The exporter uses `git archive`, so local `.env`, `.venv`, `node_modules`, untracked credentials and local runtime files are not included.

## Evidence integrity

NEXUS keeps `LIVE`, `IMPORT` and `REPLAY` explicitly separated. It does not claim global origin when only the earliest event in the collected dataset is known, and public/free fallbacks are not misrepresented as unrestricted official platform access.
