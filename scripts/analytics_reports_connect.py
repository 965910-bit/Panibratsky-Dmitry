#!/usr/bin/env python3
"""Owner-operated separate read-only Google Analytics reporting OAuth."""
import secrets
import sys
import webmaster_google_connect as google
SCOPE='https://www.googleapis.com/auth/analytics.readonly'
SECRET_NAMES=('SCM_GA4_REPORT_CLIENT_ID','SCM_GA4_REPORT_CLIENT_SECRET','SCM_GA4_REPORT_REFRESH_TOKEN')

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print('Usage: python analytics_reports_connect.py DESKTOP_OAUTH_JSON');return 2
    print('Connect Google Analytics reports. This requests analytics.readonly only.')
    print('Separate GitHub secrets; existing Analytics and Search Console secrets are not overwritten.')
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
        print('Read-only Analytics reporting secrets saved. No Analytics settings changed.')
        return 0
    except (google.SetupError,OSError,EOFError,KeyboardInterrupt):
        print('Setup failed. Some reporting secrets might already have been saved; do not retry blindly.')
        return 1
    finally:google.SCOPE,google.SECRET_NAMES=old_scope,old_names
if __name__=='__main__':sys.exit(main())
