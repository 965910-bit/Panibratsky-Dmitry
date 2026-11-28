#!/usr/bin/env python3
"""Weekly PageSpeed mobile homepage check; public page, no Google account data."""
import json
import math
import os
import subprocess
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
from webmaster_readonly import NoRedirect

SITE='https://scm-news.ru/'
ENDPOINT='https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
MAX_BYTES=8*1024*1024
class PageSpeedError(Exception):pass

def request():
    query=urllib.parse.urlencode({'url':SITE,'strategy':'mobile','category':'performance'})
    req=urllib.request.Request(ENDPOINT+'?'+query,headers={'Accept':'application/json','User-Agent':'SCM-News-PageSpeed-Monitor/1.0'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=150) as response:raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise PageSpeedError('response_too_large')
        result=json.loads(raw)
        if not isinstance(result,dict):raise PageSpeedError('invalid_response')
        return result
    except urllib.error.HTTPError as e:
        code=str(e.code) if e.code in (400,403,429,500,502,503,504) else 'other'
        raise PageSpeedError('http_'+code) from None
    except (urllib.error.URLError,TimeoutError,OSError,ValueError):raise PageSpeedError('network_or_response') from None

def local_lighthouse(*, run=subprocess.run):
    executable=Path(__file__).resolve().parents[1]/'tools/pagespeed/node_modules/.bin/lighthouse'
    args=[str(executable),SITE,'--output=json','--quiet','--only-categories=performance',
          '--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage']
    try:
        completed=run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=150,check=True)
        if len(completed.stdout)>MAX_BYTES:raise PageSpeedError('local_response_too_large')
        lighthouse=json.loads(completed.stdout)
        if not isinstance(lighthouse,dict):raise PageSpeedError('invalid_local_response')
        return {'lighthouseResult':lighthouse}
    except (OSError,subprocess.SubprocessError,UnicodeError,ValueError):raise PageSpeedError('local_lighthouse_failed') from None


def measure(*, remote=request, local=local_lighthouse):
    try:return parse(remote()),'pagespeed_api'
    except PageSpeedError as error:
        if str(error) not in ('http_429','http_403'):raise
        return parse(local()),'local_lighthouse'


def parse(data):
    if not isinstance(data,dict):raise PageSpeedError('invalid_response')
    lh=data.get('lighthouseResult')
    if not isinstance(lh,dict) or lh.get('runtimeError') or lh.get('requestedUrl')!=SITE:raise PageSpeedError('lighthouse_unavailable')
    # Never attribute redirected third-party measurements to the site.
    if lh.get('finalDisplayedUrl',lh.get('finalUrl')) not in (SITE,'https://scm-news.ru/index.html'):raise PageSpeedError('unexpected_final_url')
    categories=lh.get('categories');audits=lh.get('audits')
    if not isinstance(categories,dict) or not isinstance(audits,dict):raise PageSpeedError('missing_lighthouse_data')
    performance=categories.get('performance')
    if not isinstance(performance,dict):raise PageSpeedError('missing_score')
    score=performance.get('score')
    if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:raise PageSpeedError('invalid_score')
    def metric(name):
        audit=audits.get(name)
        if not isinstance(audit,dict) or audit.get('scoreDisplayMode') in ('error','notApplicable','manual','informative'):return None
        val=audit.get('numericValue')
        return round(val,3) if type(val) in (int,float) and math.isfinite(val) and 0<=val<=1e9 else None
    # CrUX's page-level field metrics, when supplied, are not lab results. No fallback to origin.
    field=data.get('loadingExperience',{})
    if not isinstance(field,dict):raise PageSpeedError('invalid_field_data')
    metrics=field.get('metrics',{})
    if not isinstance(metrics,dict):raise PageSpeedError('invalid_field_data')
    def field_category(key):
        v=metrics.get(key,{})
        if not isinstance(v,dict):return 'unknown'
        return {'FAST':'good','AVERAGE':'needs_improvement','SLOW':'poor'}.get(v.get('category'),'unknown')
    return {'score':round(score*100),'lcp_ms':metric('largest-contentful-paint'),
            'cls':metric('cumulative-layout-shift'),'tbt_ms':metric('total-blocking-time'),
            'field_lcp':field_category('LARGEST_CONTENTFUL_PAINT_MS'),
            'field_cls':field_category('CUMULATIVE_LAYOUT_SHIFT_SCORE'),
            'field_inp':field_category('INTERACTION_TO_NEXT_PAINT')}

def main():
    if os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':
        print('Blocked.',file=sys.stderr);return 1
    try:
        result,source=measure()
        out='; '.join(k+'='+str(v if v is not None else 'unavailable') for k,v in result.items())
        print('::notice title=PageSpeed mobile homepage::'+out+'; source='+source+'; laboratory_single_run_not_uptime; field_unknown_is_not_zero')
        summary=os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary,'a',encoding='utf-8') as f:
                f.write('## Скорость главной страницы: мобильный тест\n\n')
                f.write('Источник: '+source+'. При локальном Lighthouse полевые данные недоступны.\n\n')
                f.write('Lighthouse (лабораторный замер): '+str(result['score'])+'/100; LCP: '+str(result['lcp_ms'] if result['lcp_ms'] is not None else 'нет данных')+' мс; CLS: '+str(result['cls'] if result['cls'] is not None else 'нет данных')+'; TBT: '+str(result['tbt_ms'] if result['tbt_ms'] is not None else 'нет данных')+' мс.\n\n')
                f.write('Данные реальных пользователей CrUX (только для страницы): LCP — '+result['field_lcp']+', CLS — '+result['field_cls']+', INP — '+result['field_inp']+'. unknown означает отсутствие подтверждённых данных, не ноль.\n\n')
                f.write('Один замер может колебаться; Lighthouse не подтверждает доступность сайта в течение недели.\n')
        return 0
    except PageSpeedError as e:
        print('::error title=PageSpeed::'+str(e)+'; no_measurement',file=sys.stderr);return 1
    except Exception:
        print('::error title=PageSpeed::check_failed; no_measurement',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
