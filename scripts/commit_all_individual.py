#!/usr/bin/env python3
"""Commit every file from git status as an individual commit. Output to log file."""
import subprocess, sys, time, os

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'commit_progress.log')
def log(msg):
    with open(LOG, 'a') as f:
        f.write(msg + '\n')
    print(msg, flush=True)

def run(cmd, timeout=120):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        log(f"  ERROR running {' '.join(cmd)}: {e}")
        return None

def get_status_files():
    r = run(['git', 'status', '--porcelain', '-uall'])
    if r is None:
        return [], [], []
    files = {'D': [], 'A': [], 'M': []}
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        path = line[3:].lstrip()
        if ' -> ' in path:
            parts = path.split(' -> ')
            if len(parts) == 2:
                files['D'].append(parts[0].strip())
                files['A'].append(parts[1].strip())
            continue
        if status == 'D':
            files['D'].append(path)
        elif status == 'A':
            files['A'].append(path)
        elif status == 'M':
            files['M'].append(path)
        elif status == '??':
            files['A'].append(path)
    return files['D'], files['A'], files['M']

def commit_file(filepath, commit_type, count, total):
    basename = os.path.basename(filepath)
    msg = f"{commit_type} chore: {basename} (hermes->jarvis rebrand)"
    if count % 100 == 0 or count == 1:
        log(f"  [{count}/{total}] {commit_type}: {filepath}")
    # Use add + commit
    r = run(['git', 'add', filepath])
    if r is None or r.returncode != 0:
        if r and 'nothing to commit' not in r.stderr.lower():
            log(f"  ADD FAILED {filepath}: {r.stderr.strip()[-100:]}")
        return count  # don't increment count on failure
    r = run(['git', 'commit', '-m', msg])
    if r is None:
        return count
    if r.returncode == 0:
        return count + 1
    if 'nothing to commit' in (r.stderr + r.stdout).lower():
        return count + 1
    log(f"  COMMIT FAILED {filepath}: {r.stderr.strip()[-100:]}")
    return count

def main():
    log("=" * 60)
    log("Starting individual commit process")
    log(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"PID: {os.getpid()}")
    log("=" * 60)
    
    start = time.time()
    d_files, a_files, m_files = get_status_files()
    
    log(f"Deletions: {len(d_files)}")
    log(f"Additions: {len(a_files)}")
    log(f"Modifications: {len(m_files)}")
    total = len(d_files) + len(a_files) + len(m_files)
    log(f"Total: {total} individual commits")
    log("=" * 60)
    
    if total == 0:
        log("Nothing to commit!")
        return
    
    count = 0
    
    # Phase 1: Deletions
    log("\n=== Phase 1: Deletions ===")
    for i, f in enumerate(d_files, 1):
        count = commit_file(f, 'D', count, total)
        if i % 100 == 0:
            elapsed = time.time() - start
            rate = count / elapsed if elapsed > 0 else 0
            log(f"  Progress: {i}/{len(d_files)} deletions done ({count}/{total} total) {rate:.1f}/s")
    
    # Phase 2: Additions
    log("\n=== Phase 2: Additions ===")
    for i, f in enumerate(a_files, 1):
        count = commit_file(f, 'A', count, total)
        if i % 100 == 0:
            elapsed = time.time() - start
            rate = count / elapsed if elapsed > 0 else 0
            log(f"  Progress: {i}/{len(a_files)} additions done ({count}/{total} total) {rate:.1f}/s")
    
    # Phase 3: Modifications
    log("\n=== Phase 3: Modifications ===")
    for i, f in enumerate(m_files, 1):
        count = commit_file(f, 'M', count, total)
        if i % 100 == 0:
            elapsed = time.time() - start
            rate = count / elapsed if elapsed > 0 else 0
            log(f"  Progress: {i}/{len(m_files)} mods done ({count}/{total} total) {rate:.1f}/s")
    
    elapsed = time.time() - start
    log("\n" + "=" * 60)
    log(f"COMPLETE: {count} individual commits in {elapsed:.0f}s ({count/elapsed:.1f}/s)")
    log(f"Total commits on branch: ", end='')
    r = run(['git', 'rev-list', '--count', 'HEAD'])
    if r:
        log(r.stdout.strip())
    log(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

if __name__ == '__main__':
    # Clear old log
    open(LOG, 'w').close()
    main()
