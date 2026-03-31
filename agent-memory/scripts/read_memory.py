#!/usr/bin/env python3
"""
read_memory.py — Read agent memory files for a workspace.
Part of the agent-memory Claude Skill.
Usage: python3 read_memory.py [workspace_path]
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta

def read_memory(workspace: str = '.') -> None:
    ws = Path(workspace).resolve()
    global_dir = Path.home() / '.workbuddy'
    mem_dir = ws / '.workbuddy' / 'memory'
    
    print(f"=== Agent Memory Reader ===")
    print(f"Workspace: {ws}")
    print()
    
    total_size = 0
    
    # Global identity files
    print("--- Global Identity ---")
    for name in ['SOUL.md', 'IDENTITY.md', 'USER.md']:
        f = global_dir / name
        if f.exists():
            size = f.stat().st_size
            total_size += size
            print(f"  ✓ {name}: {size:,} chars")
        else:
            print(f"  ✗ {name}: not found")
    
    print()
    print("--- Project Memory ---")
    
    mem_file = mem_dir / 'MEMORY.md'
    if mem_file.exists():
        size = mem_file.stat().st_size
        total_size += size
        print(f"  ✓ MEMORY.md: {size:,} chars")
    else:
        print(f"  ✗ MEMORY.md: not found")
    
    # Daily logs
    if mem_dir.exists():
        logs = sorted(mem_dir.glob('????-??-??.md'))
        print(f"  ✓ Daily logs: {len(logs)} files")
        if logs:
            print(f"    Range: {logs[0].stem} → {logs[-1].stem}")
            # Show recent
            for log in logs[-3:]:
                size = log.stat().st_size
                total_size += size
                print(f"    - {log.name}: {size:,} chars")
    else:
        print(f"  ✗ Memory directory not found: {mem_dir}")
    
    print()
    print(f"Total memory size: {total_size:,} chars ({total_size/1024:.1f} KB)")
    
    # Recommendations
    if total_size > 15000:
        print("\n⚠ Memory exceeds 15KB — consider distilling old daily logs into MEMORY.md")
    if total_size < 500:
        print("\n⚠ Memory appears empty — agent may lose context between sessions")
    else:
        print("\n✓ Memory system looks healthy")


if __name__ == '__main__':
    workspace = sys.argv[1] if len(sys.argv) > 1 else '.'
    read_memory(workspace)
