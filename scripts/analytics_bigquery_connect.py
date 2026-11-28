#!/usr/bin/env python3
"""Owner-operated OAuth for BigQuery read-only metadata. No billing permissions."""
import secrets,sys
import webmaster_google_connect as google
SCOPE='https://www.googleapis.com/auth/bigquery.readonly'
SECRET_NAMES=('SCM_BQ_READ_CLIENT_ID','SCM_BQ_READ_CLIENT_SECRET','SCM_BQ_READ_REFRESH_TOKEN')

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print('Usage: python analytics_bigquery_connect.py DESKTOP_OAUTH_JSON');return 2
    print('Connect BigQuery with bigquery.readonly. Existing GA and Search Console connections are not overwritten.')
    print('This scope permits reading BigQuery data available to this Google account, not just metadata.')
    print('IAM access and the enabled BigQuery API are still needed. No billing or settings will be changed.')
    old_scope,old_names=google.SCOPE,google.SECRET_NAMES
    try:
        if input('Continue? Type ДА: ').strip().upper()!='ДА':
            print('Cancelled. No changes made.');return 0
        google.SCOPE=SCOPE;google.SECRET_NAMES=SECRET_NAMES
        cid,secret=google.load_desktop_client(args[0]);repo=google.gh_check()
        verifier,challenge=google.pkce();state=secrets.token_urlsafe(32)
        code,redirect=google.receive_code(cid,state,challenge)
        refresh=google.exchange(code,redirect,cid,secret,verifier)
        google.gh_store(repo,cid,secret,refresh)
        print('Separate BigQuery secrets saved. Dataset and billing access are not yet verified.')
        return 0
    except (google.SetupError,OSError,EOFError,KeyboardInterrupt):
        print('Setup failed. Some secrets might already have been saved; do not retry blindly.')
        return 1
    finally:google.SCOPE,google.SECRET_NAMES=old_scope,old_names
if __name__=='__main__':sys.exit(main())
