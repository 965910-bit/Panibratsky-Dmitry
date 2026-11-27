#!/usr/bin/env python3
"""Read-only, bounded Yandex recrawl status checks; never resubmit tasks."""
import re
from urllib.parse import quote
from webmaster_actions import api, YANDEX_API, SITE, ActionError

UUID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')


def check_receipts(queue, token, *, limit=20, request=api):
    if not isinstance(token, str) or not token or '\r' in token or '\n' in token:
        raise ActionError('invalid access token')
    receipts = queue.unchecked_receipts(limit)
    if not receipts:
        return {'status':'ok', 'tasks':[], 'indexing_guaranteed':False}
    # Fail without changing observations if the identity or host cannot be verified.
    user = request(YANDEX_API + '/user', token, 'OAuth').get('user_id')
    if type(user) is not int or user < 1:
        raise ActionError('invalid user')
    hosts_url = YANDEX_API + '/user/' + str(user) + '/hosts'
    hosts = request(hosts_url, token, 'OAuth').get('hosts')
    if not isinstance(hosts, list):
        raise ActionError('invalid hosts')
    matches = [h for h in hosts if isinstance(h,dict) and h.get('ascii_host_url') == SITE and h.get('verified') is True and isinstance(h.get('host_id'),str) and h['host_id']]
    if len(matches) != 1:
        raise ActionError('verified exact host unavailable')
    base = hosts_url + '/' + quote(matches[0]['host_id'],safe='') + '/recrawl/queue/'
    output = []
    for task, url, revision in receipts:
        state = None
        try:
            if not UUID.fullmatch(task):
                raise ActionError('invalid task id')
            response = request(base + quote(task,safe=''), token, 'OAuth')
            if (response.get('task_id') != task or response.get('url') != url or
                response.get('state') not in ('IN_PROGRESS','DONE','FAILED')):
                raise ActionError('invalid task response')
            state = response['state']
        except Exception:
            # TASK_NOT_FOUND, malformed data and access errors are unknown, not failures to crawl.
            pass
        queue.record_observation(task,url,revision,state)
        output.append({'task_id':task,'url':url,'revision':revision,'status':state or 'UNKNOWN'})
    return {'status':'partial' if any(x['status']=='UNKNOWN' for x in output) else 'ok',
            'tasks':output, 'indexing_guaranteed':False}
