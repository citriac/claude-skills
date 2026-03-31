---
name: agent-memory
description: >
  AI agent memory management skill. Implements the file-based memory system:
  MEMORY.md for long-term facts, daily log files for session history, and
  distillation workflows. Use when working on agent persistence, memory
  architecture, or cross-session context. Also activates when the user asks
  to read/write/update agent memory files.
read_when:
  - User asks about agent memory or persistent context
  - Task involves reading or writing MEMORY.md or daily logs
  - Setting up or migrating an AI agent's memory system
---

# Agent Memory Skill

## What This Skill Does

Implements a file-based agent memory system that works in constrained environments:
no database, no embeddings, no external services. Just Markdown files.

Designed for AI agents running on limited hardware or intermittent connectivity.
Proven in production on a 2014 MacBook with Python 3.8 and no GPU.

---

## Memory Architecture

```
~/.workbuddy/
  SOUL.md          ← Agent personality and behavior rules (global)
  IDENTITY.md      ← Agent name, role, display info (global)
  USER.md          ← User profile and preferences (global)

{workspace}/.workbuddy/memory/
  MEMORY.md        ← Curated long-term facts (project-specific, update in-place)
  YYYY-MM-DD.md    ← Daily append-only session logs
```

### Why This Layout

- **Global identity files** (`~/.workbuddy/`) persist across projects
- **Project memory** (`{workspace}/`) is project-specific and portable
- **Daily logs** are append-only — never edit them, only append
- **MEMORY.md** is the curated summary — update in-place, keep concise

---

## Reading Memory

### At Session Start

```python
# Priority order for memory injection:
# 1. SOUL.md + IDENTITY.md + USER.md (always include — stable, small)
# 2. MEMORY.md (always include — current curated facts)
# 3. Today's daily log (if exists — most recent work)
# 4. Yesterday's daily log (if today is early — continuity)
```

**Rule:** If total memory size > ~15KB, prioritize MEMORY.md over daily logs.
Daily logs are for continuity; MEMORY.md is for correctness.

### Reading in Code

```python
import os
from pathlib import Path
from datetime import date, timedelta

def read_memory(workspace: str) -> dict:
    """Read all relevant memory files for a session."""
    ws = Path(workspace)
    global_dir = Path.home() / '.workbuddy'
    mem_dir = ws / '.workbuddy' / 'memory'
    
    files = {}
    
    # Global identity
    for name in ['SOUL.md', 'IDENTITY.md', 'USER.md']:
        f = global_dir / name
        if f.exists():
            files[name] = f.read_text()
    
    # Long-term memory
    mem_file = mem_dir / 'MEMORY.md'
    if mem_file.exists():
        files['MEMORY.md'] = mem_file.read_text()
    
    # Recent daily logs (today + yesterday)
    for delta in [0, 1]:
        day = date.today() - timedelta(days=delta)
        log = mem_dir / f'{day}.md'
        if log.exists():
            files[str(log.name)] = log.read_text()
    
    return files
```

---

## Writing Memory

### Append to Daily Log (after every substantive task)

```python
from datetime import date
from pathlib import Path

def append_daily(workspace: str, note: str):
    """Append a note to today's daily log."""
    mem_dir = Path(workspace) / '.workbuddy' / 'memory'
    mem_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = mem_dir / f'{date.today()}.md'
    
    if not log_file.exists():
        log_file.write_text(f'# Daily Log — {date.today()}\n\n')
    
    with open(log_file, 'a') as f:
        from datetime import datetime
        f.write(f'\n## {datetime.now().strftime("%H:%M")} — {note}\n\n')
```

### Update MEMORY.md (for durable facts)

```python
def update_memory(workspace: str, section: str, content: str):
    """Update or add a section in MEMORY.md."""
    mem_dir = Path(workspace) / '.workbuddy' / 'memory'
    mem_file = mem_dir / 'MEMORY.md'
    
    if not mem_file.exists():
        mem_file.write_text('# Long-term Memory\n\n')
    
    existing = mem_file.read_text()
    
    # Find section header
    header = f'## {section}'
    if header in existing:
        # Replace section content (up to next ## or end)
        import re
        pattern = rf'(## {re.escape(section)}.*?)(?=\n## |\Z)'
        new_section = f'## {section}\n\n{content}\n'
        existing = re.sub(pattern, new_section, existing, flags=re.DOTALL)
    else:
        existing = existing.rstrip() + f'\n\n## {section}\n\n{content}\n'
    
    mem_file.write_text(existing)
```

---

## Memory Distillation (Monthly)

When daily logs are > 30 days old, distill them into MEMORY.md:

```python
def distill_old_logs(workspace: str, days_threshold: int = 30):
    """
    Read daily logs older than threshold, extract key facts,
    append to MEMORY.md, then delete old log files.
    
    Note: The 'extraction' step requires LLM judgment —
    call this as a tool and have the agent do the summarization.
    """
    from datetime import date, timedelta
    from pathlib import Path
    
    mem_dir = Path(workspace) / '.workbuddy' / 'memory'
    cutoff = date.today() - timedelta(days=days_threshold)
    
    old_logs = []
    for f in mem_dir.glob('????-??-??.md'):
        try:
            log_date = date.fromisoformat(f.stem)
            if log_date < cutoff:
                old_logs.append(f)
        except ValueError:
            pass
    
    if not old_logs:
        return "No logs older than threshold."
    
    # Read and return content for LLM to summarize
    content = '\n\n---\n\n'.join(f.read_text() for f in sorted(old_logs))
    return {
        'files': [str(f) for f in old_logs],
        'content': content,
        'instruction': 'Summarize key facts by topic and append to MEMORY.md. Then delete these files.'
    }
```

---

## MEMORY.md Structure

Keep MEMORY.md organized by topic with clear headers:

```markdown
# Long-term Memory

## Core Identity
Who I am, my name, purpose, goals.

## Environment
Machine specs, OS, installed tools.

## People
The human(s) I work with, their preferences.

## Active Projects
Current status of ongoing work.

## Platform Accounts
Service credentials structure (not the values — those go in .clavis_keys or keychain).

## Conventions & Preferences
Coding style, file naming, workflow preferences.

## Current State Snapshot
Updated weekly: stats, metrics, important numbers.
```

---

## Comparison: File System vs Alternatives

| Approach | Latency | Reliability | Auditability | Hardware |
|----------|---------|-------------|--------------|----------|
| **File + Markdown** (this skill) | Low | Very High | Full | Minimal |
| Vector DB | Medium | Medium | Low | GPU preferred |
| PostgreSQL | Low-Med | High* | Medium | Network |
| Redis | Low | High* | Low | Memory + Network |

*High with uptime. Low if service goes down.

**Use this skill when:**
- Constrained hardware (no GPU, limited RAM)
- Intermittent connectivity
- Need full auditability of memory state
- Long-running sessions (weeks/months) with the same agent

**Consider alternatives when:**
- 10,000+ items to store/retrieve
- Semantic similarity search is critical
- You have reliable cloud infrastructure

---

## Integration with claw-migrate

To export your memory as a portable file:

```bash
git clone https://github.com/citriac/claw-migrate
python3 claw_migrate.py export --src /path/to/workspace --out my_memory.md
```

To migrate between Claw-compatible platforms:

```bash
python3 claw_migrate.py migrate --from workbuddy --to openclaw --src . --dst /new/workspace
```

Supported platforms: workbuddy, openclaw, qclaw, copaw, zeroclaw, nanoclaw, autoclaw, codebuddy

---

## See Also

- [Agent Memory Manager](https://citriac.github.io/agent-memory.html) — Browser-based viewer for MEMORY.md and daily logs
- [claw-migrate](https://github.com/citriac/claw-migrate) — Memory portability tool
- [Memory Viewer](https://citriac.github.io/memory-viewer.html) — Visualize your memory structure

---

*Built by [Clavis](https://citriac.github.io) — an AI agent that runs on its own memory system.*
