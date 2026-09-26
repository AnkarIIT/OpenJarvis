#!/usr/bin/env python3
"""Commit remaining deletions one at a time."""
import subprocess, os, sys, time

def git(*args):
    try:
        return subprocess.run(['git'] + list(args), capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f'  Git error: {e}', flush=True)
        return None

# Get remaining deletions
r = git('ls-files', '--deleted')
if r is None:
    print('Failed to get deletions')
    sys.exit(1)

deletions = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
print(f'Deletions remaining: {len(deletions)}', flush=True)

if not deletions:
    print('No deletions remaining!')
    sys.exit(0)

count = 0
errors = 0
start = time.time()

for i, f in enumerate(deletions):
    try:
        g1 = git('rm', '--', f)
        if g1.returncode != 0:
            print(f'  rm failed for {f}: {g1.stderr.strip()[-100:]}', flush=True)
            errors += 1
            continue
        g2 = git('commit', '-m', f'D chore: delete {os.path.basename(f)} (hermes->jarvis rebrand)')
        if g2.returncode != 0:
            print(f'  commit failed for {f}: {g2.stderr.strip()[-100:]}', flush=True)
            errors += 1
            continue
        count += 1
        if count % 20 == 0:
            elapsed = time.time() - start
            rate = count / elapsed if elapsed > 0 else 0
            remaining = len(deletions) - count
            eta = remaining / rate if rate > 0 else 0
            print(f'  {count}/{len(deletions)} done ({rate:.1f}/s, ETA {eta:.0f}s, errors: {errors})', flush=True)
    except Exception as e:
        print(f'  Exception on {f}: {e}', flush=True)
        errors += 1

elapsed = time.time() - start
print(f'\nDone! {count} commits created, {errors} errors in {elapsed:.0f}s')
print(f'Rate: {count/elapsed:.1f} commits/s' if elapsed > 0 else 'N/A')
