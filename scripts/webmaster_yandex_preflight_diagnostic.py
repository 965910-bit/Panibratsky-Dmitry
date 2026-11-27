#!/usr/bin/env python3
"""Diagnose sitemap production prerequisites without calling Yandex."""
import json
import os
import re
import sys
import indexnow_submit as ix


def run(repo, token, *, git=ix.git, fetch=ix.request, validate=ix.validate_live):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not token:
        return 'configuration'
    try:
        sha=git('rev-parse','HEAD')
        if not re.fullmatch(r'[a-f0-9]{40}',sha):return 'checkout'
        root='https://api.github.com/repos/'+repo
        _,_,raw=fetch(root+'/git/ref/heads/main',token=token)
        if json.loads(raw)['object']['sha']!=sha:return 'main_mismatch'
    except Exception:return 'github_main_unavailable'
    try:
        _,_,raw=fetch(root+'/pages/builds/latest',token=token)
        build=json.loads(raw)
        if build.get('status')!='built' or build.get('commit')!=sha:return 'pages_mismatch'
    except Exception:return 'github_pages_unavailable'
    try:
        validate([])
    except Exception:return 'live_preflight_failed'
    return 'ok'


def main():
    result=run(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_TOKEN',''))
    print('::notice title=Sitemap production preflight::'+result)
    return 0 if result=='ok' else 1

if __name__=='__main__':sys.exit(main())
