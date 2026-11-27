#!/usr/bin/env python3
"""Immutable git-diff adapters for Queue.enqueue_deployment; no network calls."""
import subprocess
from indexnow_submit import ROOT, changed_urls


def is_ancestor(old, new):
    result = subprocess.run(['git','merge-base','--is-ancestor',old,new], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError('unable to verify git ancestry')


def changed_canonical(old, new):
    result = subprocess.run(['git','diff','--name-only','--diff-filter=AM',old,new,'--'],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    return changed_urls(result.stdout.splitlines())
