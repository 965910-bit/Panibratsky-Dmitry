#!/usr/bin/env python3
"""Owner-operated Google Analytics OAuth onboarding; no Analytics changes.

Runs as a separate process. Existing Search Console secrets are never overwritten.
"""
import secrets
import sys
import webmaster_google_connect as google

SCOPE='https://www.googleapis.com/auth/analytics.edit'
SECRET_NAMES=('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print('Запуск: python analytics_google_connect.py ПУТЬ_К_DESKTOP_OAUTH_JSON');return 2
    print('Подключение Google Analytics для scm-news.ru.')
    print('Права analytics.edit позволяют читать и изменять настройки Analytics, включая ключевые события.')
    print('Доступ Search Console не заменяется. Эта программа не меняет настройки Analytics.')
    old_scope,old_names=google.SCOPE,google.SECRET_NAMES
    try:
        if input('Продолжить? Введите ДА: ').strip().upper()!='ДА':
            print('Отменено. Изменений не выполняли.');return 0
        # Shared helpers operate only in this short-lived process, never in the
        # already-configured Search Console workflow. Use distinct secret names.
        google.SCOPE=SCOPE
        google.SECRET_NAMES=SECRET_NAMES
        cid,secret=google.load_desktop_client(args[0]);repo=google.gh_check()
        verifier,challenge=google.pkce();state=secrets.token_urlsafe(32)
        code,redirect=google.receive_code(cid,state,challenge)
        refresh=google.exchange(code,redirect,cid,secret,verifier)
        google.gh_store(repo,cid,secret,refresh)
        print('Доступ Google Analytics сохранён в отдельных секретах GitHub; настройки Analytics не менялись.')
        print('Далее проверим ресурс и существующие события перед созданием целей.')
        return 0
    except (google.SetupError,OSError,EOFError,KeyboardInterrupt):
        print('Не удалось завершить подключение. Возможно, часть новых секретов уже создана; не повторяйте вслепую.')
        return 1
    finally:
        google.SCOPE,google.SECRET_NAMES=old_scope,old_names
if __name__=='__main__':sys.exit(main())
