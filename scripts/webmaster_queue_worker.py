#!/usr/bin/env python3
"""Explicit single-worker queue drain primitive; no scheduler or token storage.

Caller must serialize workers and enqueue in deployment order, use durable local
storage and select a verified current deployment checkout. This module does not
provide these guarantees. Do not connect it to ephemeral GitHub runners.
"""
from indexnow_submit import validate_live
from webmaster_actions import yandex_action


class WorkerError(Exception):
    pass


def recrawl_only(token, urls, apply):
    """Do not call the separate Sitemap-management endpoint when draining."""
    return yandex_action(token, urls, apply, manage_sitemap=False)


def drain(queue, token, *, limit=5, validate=validate_live, action=recrawl_only):
    """Submit at most five individual URLs; stop on exhausted quota or ambiguity.

    The caller must confirm the checkout is current main and a successful Pages
    deployment. validate_live checks the current file bytes against production;
    enqueued revision is a generation marker, not the file version to deploy.
    """
    if not isinstance(token, str) or not token or '\n' in token or '\r' in token:
        raise WorkerError('missing or invalid access token')
    if type(limit) is not int or not 1 <= limit <= 5:
        raise WorkerError('invalid batch limit')
    results = []
    for _ in range(limit):
        claim = queue.claim()
        if claim is None:
            if any(row[3] in ('in_flight', 'uncertain') for row in queue.items()):
                return {'status':'blocked', 'results':results}
            break
        url, revision = claim
        try:
            validate([url])
        except Exception:
            queue.release_unattempted(url, revision)
            return {'status':'preflight_failed', 'results':results}
        # From here onward a provider write may happen. A crash leaves the claim
        # in-flight and recovery requires reconciliation, never a blind retry.
        try:
            response = action(token, [url], True)
            entries = response.get('recrawl')
            if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
                raise WorkerError('invalid provider response')
            entry = entries[0]
            status = entry.get('status')
            if entry.get('url') != url or status not in ('accepted','already_added','quota_exhausted'):
                raise WorkerError('invalid provider response')
            task = entry.get('task_id') if status == 'accepted' else None
            if status == 'accepted' and (not isinstance(task,str) or not task or len(task) > 512):
                raise WorkerError('invalid provider response')
        except Exception:
            queue.finish(url, revision, 'uncertain')
            results.append({'url':url, 'status':'uncertain'})
            return {'status':'uncertain', 'results':results}
        # Do not catch a persistence failure here: an in-flight claim is safer
        # than reporting success without recording it durably.
        queue.finish(url, revision, status, task)
        results.append({'url':url, 'status':status})
        if status == 'quota_exhausted':
            return {'status':'quota_exhausted', 'results':results}
    return {'status':'ok', 'results':results}
