#!/usr/bin/env python3
"""One-off encrypted export of prior GA4 key-event configuration, no GA writes."""
import base64
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from analytics_ga4_diagnostic import AnalyticsError, GOALS, PROPERTY, inventory, pages
from live_seo_issue import request

PUBLIC_KEY=Path(__file__).with_name('ga4_backup_public_key.pem')
MARKER='<!-- scm-ga4-encrypted-backup:v1 -->'


def encrypt(data, public_key=PUBLIC_KEY):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    pub=serialization.load_pem_public_key(public_key.read_bytes())
    if not isinstance(pub,rsa.RSAPublicKey) or pub.key_size < 3072:raise AnalyticsError('invalid key')
    key=os.urandom(32);nonce=os.urandom(12)
    ciphertext=AESGCM(key).encrypt(nonce,data,MARKER.encode())
    wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return {'version':1,'cipher':'AES-256-GCM+RSA-OAEP-SHA256',
            'key':base64.b64encode(wrapped).decode(), 'nonce':base64.b64encode(nonce).decode(),
            'ciphertext':base64.b64encode(ciphertext).decode()}


def backup(creds, repo, token, *, find=inventory, list_pages=pages, seal=encrypt, post=request):
    if repo!='965910-bit/Panibratsky-Dmitry' or not token or '\n' in token or '\r' in token:raise AnalyticsError('invalid target')
    info=find(*creds,include_private=True)
    prop=info.get('property')
    if not info.get('domain_matches') or not info.get('can_edit') or not isinstance(prop,str) or not PROPERTY.fullmatch(prop):raise AnalyticsError('identity mismatch')
    events=list_pages(prop+'/keyEvents','keyEvents',info['token'])
    if len(events)!=info['key_event_count'] or any(not isinstance(e,dict) or not isinstance(e.get('eventName'),str) for e in events):raise AnalyticsError('inconsistent inventory')
    names=[e['eventName'] for e in events]
    if len(set(names))!=len(names) or set(names).intersection(GOALS)!=set(info['present']):raise AnalyticsError('state changed')
    old=[e for e in events if e['eventName'] not in GOALS]
    if sum(e.get('custom',False) is True and e.get('deletable',False) is True for e in old)!=info['old_custom_deletable']:raise AnalyticsError('old count changed')
    doc={'schema':1,'captured_at':datetime.now(timezone.utc).isoformat(), 'property':prop,'key_events':old}
    raw=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode()
    if len(raw)>32768:raise AnalyticsError('backup exceeds bound')
    sealed=seal(raw)
    body=MARKER+'\n\nEncrypted GA4 configuration backup; key retained privately.\n\n```json\n'+json.dumps(sealed,separators=(',',':'))+'\n```'
    if len(body)>60000:raise AnalyticsError('encrypted backup exceeds bound')
    result=post('https://api.github.com/repos/'+repo+'/issues/244/comments',token,method='POST',body={'body':body})
    if not isinstance(result,dict) or type(result.get('id')) is not int or result['id']<1:raise AnalyticsError('unconfirmed backup')
    return len(old), result['id']


def main():
    if os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':
        print('Blocked.',file=sys.stderr);return 1
    creds=[os.environ.pop(x,'') for x in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        count,comment=backup(creds,os.environ.get('GITHUB_REPOSITORY',''),token)
        print(f'::notice title=Encrypted GA4 backup::old_events={count}; comment_id={comment}; ga4_writes=0; restore_verification_required')
        return 0
    except Exception:
        print('::error title=Encrypted GA4 backup::failed_or_unconfirmed; ga4_writes=0; reconcile_before_repeating',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
