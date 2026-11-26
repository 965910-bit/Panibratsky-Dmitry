#!/usr/bin/env python3
"""Prepare and submit one data-only publication PR. Never force-pushes.

Requires an independently installed, repository-scoped GitHub App token in
GH_TOKEN and an active ruleset without bypasses. Intended only for trusted
main-branch scheduled workflows, after their collection/validation steps.
"""
import argparse
import json
import os
import re
import subprocess
import sys

from check_publication_candidate import check as check_candidate
from run_summary import report

APP_LOGIN = 'scm-news-publication-965910[bot]'
PATHS = {
    'news': ['data/news.json', 'trends.html', 'sitemap.xml', 'rss.xml'],
    'open-data': ['data/open-logistics.json', 'data/open-logistics-archives'],
}
TITLES = {'news': 'Автоматическое обновление новостей', 'open-data': 'Автоматическое обновление открытых данных'}


def command(*args, capture=True):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def api(endpoint, *args):
    return json.loads(command('gh', 'api', endpoint, *args))


def validate_policy(repo, rules, details):
    if not repo.get('allow_auto_merge') or repo.get('default_branch') != 'main':
        raise ValueError('Auto-merge must be enabled and main must be the default branch')
    ids = {r.get('ruleset_id') for r in rules if r.get('ruleset_id') is not None}
    for rule_id in ids:
        d = details.get(rule_id, {})
        if (d.get('enforcement') != 'active' or d.get('current_user_can_bypass') != 'never'
                or type(d.get('bypass_count')) is not int or d['bypass_count'] != 0
                or ('bypass_actors' in d and d['bypass_actors'] != [])):
            continue
        effective = [r for r in rules if r.get('ruleset_id') == rule_id]
        pr_rules = [r.get('parameters') or {} for r in effective if r.get('type') == 'pull_request']
        # A human-review requirement would make this path non-automatic. Never bypass it.
        if not any(p.get('required_approving_review_count') == 0
                   and not p.get('require_code_owner_review')
                   and not p.get('require_last_push_approval')
                   and not p.get('required_review_thread_resolution') for p in pr_rules):
            continue
        for rule in effective:
            if rule.get('type') != 'required_status_checks':
                continue
            params = rule.get('parameters') or {}
            checks = params.get('required_status_checks') or []
            if (params.get('strict_required_status_checks_policy') is True and
                    any(c.get('context') == 'validate' and c.get('integration_id') == 15368 for c in checks)):
                return
    raise ValueError('Need an active no-bypass ruleset requiring PR and strict validate from GitHub Actions')


def policy(repository):
    repo = api('repos/' + repository)
    rules = api('repos/' + repository + '/rules/branches/main')
    ids = {r.get('ruleset_id') for r in rules if r.get('ruleset_id') is not None}
    details = {}
    query = 'query($id: ID!) { node(id: $id) { ... on RepositoryRuleset { bypassActors { totalCount } } } }'
    for i in ids:
        detail = api(f'repos/{repository}/rulesets/{i}')
        data = api('graphql', '-f', 'query=' + query, '-f', 'id=' + detail['node_id'])
        if data.get('errors'):
            raise ValueError('Unable to verify ruleset bypass count')
        detail['bypass_count'] = data['data']['node']['bypassActors']['totalCount']
        details[i] = detail
    validate_policy(repo, rules, details)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=PATHS)
    args = parser.parse_args()
    try:
        repository = os.environ['GITHUB_REPOSITORY']
        base = os.environ['GITHUB_SHA']
        run_id = os.environ['GITHUB_RUN_ID']
        attempt = os.environ['GITHUB_RUN_ATTEMPT']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository name')
        if not re.fullmatch(r'[0-9a-f]{40}', base) or not run_id.isdigit() or not attempt.isdigit():
            raise ValueError('Invalid workflow identity')
        if os.environ.get('GITHUB_REF') != 'refs/heads/main' or not os.environ.get('GH_TOKEN'):
            raise ValueError('A main-branch run and app token are required')
        policy(repository)
        branch_info = api(f'repos/{repository}/branches/main')
        if branch_info['commit']['sha'] != base or not branch_info.get('protected'):
            raise ValueError('Main advanced or is not protected; rerun from the new base')
        if command('git', 'rev-parse', 'HEAD') != base:
            raise ValueError('Checkout does not match workflow base')
        # Each kind has at most one open publication PR; do not overwrite or force-update it.
        pulls = api(f'repos/{repository}/pulls?state=open&per_page=100', '--paginate', '--slurp')
        prefix = f'scm-publication/{args.kind}/'
        if any(p.get('head', {}).get('ref', '').startswith(prefix) for page in pulls for p in page):
            raise ValueError('An earlier publication PR is still open; resolve it before retrying')
        command('git', 'config', '--local', 'user.email', 'action@github.com')
        command('git', 'config', '--local', 'user.name', 'GitHub Action')
        command('git', 'add', '--', *PATHS[args.kind])
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
        if result.returncode == 0:
            report('ℹ️ Публикация: изменений нет, PR не создан; автоматическое слияние и развёртывание этим запуском не проверялись.')
            return 0
        if result.returncode != 1:
            raise ValueError('Unable to inspect staged changes')
        command('git', 'commit', '-m', TITLES[args.kind])
        head = command('git', 'rev-parse', 'HEAD')
        check_candidate('.', base, head, args.kind)
        # A fresh base is mandatory; a concurrent update must cause a safe failure.
        if api(f'repos/{repository}/branches/main')['commit']['sha'] != base:
            raise ValueError('Main advanced during generation; retry with fresh data')
        branch = prefix + run_id + '-' + attempt
        command('gh', 'auth', 'setup-git')
        command('git', 'push', 'origin', f'{head}:refs/heads/{branch}')
        pull = api(f'repos/{repository}/pulls', '-X', 'POST',
                   '-f', 'title=' + TITLES[args.kind], '-f', 'head=' + branch,
                   '-f', 'base=main', '-f', 'body=Автоматическое обновление данных. Обязательная проверка выполняется до слияния.')
        if (pull.get('user', {}).get('login') != APP_LOGIN or pull.get('head', {}).get('sha') != head
                or pull.get('base', {}).get('ref') != 'main'):
            raise ValueError('Created PR identity or head mismatch; manual review required')
        # Recheck policy before requesting auto-merge; GitHub enforces required checks.
        policy(repository)
        mutation = '''mutation($id: ID!, $head: GitObjectID!) {
          enablePullRequestAutoMerge(input:{pullRequestId:$id, expectedHeadOid:$head, mergeMethod:MERGE}) {
            pullRequest { number autoMergeRequest { enabledAt } }
          }
        }'''
        response = api('graphql', '-f', 'query=' + mutation,
                       '-f', 'id=' + pull['node_id'], '-f', 'head=' + head)
        if response.get('errors') or not response.get('data', {}).get('enablePullRequestAutoMerge', {}).get('pullRequest', {}).get('autoMergeRequest'):
            raise ValueError('Auto-merge was not enabled; manual review required')
        report('⏳ Публикация: PR создан, автослияние запрошено; проверки, слияние и развёртывание ещё не подтверждены.')
        print('Publication PR created; waiting for required GitHub checks:', pull['html_url'])
        return 0
    except (KeyError, ValueError, TypeError, AttributeError, UnicodeError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        # Never print command stderr or credentials. Failure must remain visible.
        report('❌ Публикация: выполнение прервано; создание PR или слияние не подтверждены. Проверьте журнал и открытые PR.')
        print(f'Publication PR failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
