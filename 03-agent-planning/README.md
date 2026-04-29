# 03 — Morning Planning Agent

A Python agent that reads your Trello board, Google Calendar, and Gmail inbox,
then uses Claude to produce a prioritized daily plan — every morning, in seconds.

## Architecture

```
main.py                  ← entry point & agentic loop
├── prompts/
│   └── system.py        ← stable system prompt (prompt-cached)
└── tools/
    ├── trello.py        ← Trello REST API integration
    ├── calendar.py      ← Google Calendar API integration
    └── gmail.py         ← Gmail API integration
```

### How it works

```
User runs main.py
      │
      ▼
Claude (claude-opus-4-7)
      │  decides which tools to call
      ▼
Tool loop (in main.py)
   ├── get_trello_tasks    → trello.py   → Trello REST API
   ├── get_calendar_events → calendar.py → Google Calendar API
   └── get_gmail_threads   → gmail.py    → Gmail API
      │
      ▼
Claude synthesizes results
      │
      ▼
Printed daily plan
```

Each tool module exposes:
- `TOOL_DEFINITION` — JSON schema registered with the Anthropic API
- `run(tool_input)` — called by the agentic loop when Claude requests the tool

### Key design decisions

| Decision | Rationale |
|---|---|
| **Manual agentic loop** | Lets us log every tool call for transparency and debugging |
| **Prompt caching** on system prompt | The system prompt is identical on every run — caching saves ~90% of those input tokens |
| **`claude-opus-4-7` + adaptive thinking** | Best reasoning for synthesizing cross-source priorities |
| **Tool results as JSON strings** | Avoids multipart content complexity; Claude parses JSON natively |
| **No streaming for tool calls** | Tool phases are fast; streaming is added for the final plan output if desired |

## Setup

### 1. Install dependencies

```bash
pip install anthropic httpx google-auth google-api-python-client
```

### 2. Set environment variables

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Trello
export TRELLO_API_KEY="..."
export TRELLO_TOKEN="..."
export TRELLO_BOARD_ID="..."          # board ID from the board URL

# Google (service account — recommended for automation)
export GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
export GMAIL_IMPERSONATE_EMAIL="you@yourdomain.com"   # required for Gmail via SA

# Optional personalisation
export USER_NAME="Alice"
export USER_TIMEZONE="Europe/Paris"
```

> **OAuth2 alternative:** set `GOOGLE_APPLICATION_DEFAULT_CREDENTIALS` or run
> `gcloud auth application-default login` and omit `GOOGLE_SERVICE_ACCOUNT_FILE`.

### 3. Run

```bash
python main.py
```

## Getting credentials

### Trello

1. Generate an API key at <https://trello.com/power-ups/admin>
2. Generate a token via:
   `https://trello.com/1/authorize?expiration=never&scope=read&response_type=token&key=YOUR_KEY`
3. Find your board ID in the board URL: `trello.com/b/<BOARD_ID>/...`

### Google (Calendar + Gmail)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **Calendar API** and **Gmail API**
3. Create a **Service Account**, download the JSON key
4. Share your calendar with the service account email
5. For Gmail, enable [domain-wide delegation](https://admin.google.com) and
   set `GMAIL_IMPERSONATE_EMAIL` to your Google Workspace email

## Extending the agent

| Want to add… | Where to look |
|---|---|
| Slack messages | Add `tools/slack.py` following the same pattern, register in `main.py` |
| Linear/Jira tickets | Same pattern — `TOOL_DEFINITION` + `run()` |
| Scheduled daily run | Use cron or a task scheduler pointing at `python main.py` |
| Richer output (HTML, email) | Post-process the string returned by `run_agent()` |
| Streaming the final plan | Replace `client.messages.create` with `client.messages.stream` for the last turn |

## Output example

```
============================================================
YOUR MORNING PLAN
============================================================

**Morning focus**
- Finish the Q2 budget proposal (due today on Trello, high priority)
- Prep for the 10:00 product sync

**Scheduled blocks**
- 10:00–11:00  Product Sync  (Google Meet) — 5 attendees
- 14:00–14:30  1:1 with manager

**Quick wins**
- Reply to Sarah re: design review (< 5 min)
- Move "Update staging env" card to Done

**Emails requiring a reply**
- "Contract renewal — action needed" from legal@acme.com
- "PR review request: auth refactor" from dev-team@acme.com

**Deferred**
- Blog post draft (no due date, no red label)
```
