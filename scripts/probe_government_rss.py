#!/usr/bin/env python3
"""Read-only, fail-closed HTTPS availability probe; never imports or publishes news."""
import ssl
import sys
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = 'https://government.ru'
URL = ROOT + '/news/rss/'
AGENT = 'SCM-News-Source-Check'
MAX_BYTES = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(opener, url, accept):
    request = urllib.request.Request(url, headers={'Accept': accept, 'User-Agent': AGENT + '/1.0'})
    with opener.open(request, timeout=20) as response:
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError('response-too-large')
    return content


def check(opener=None):
    opener = opener or urllib.request.build_opener(NoRedirect)
    try:
        robots = fetch(opener, ROOT + '/robots.txt', 'text/plain').decode('utf-8-sig')
        if (not any(line.split('#', 1)[0].strip().lower().startswith('user-agent:')
                    for line in robots.splitlines())
                or '<html' in robots.lower() or '<!doctype' in robots.lower()):
            return False, 'robots-invalid'
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(robots.splitlines())
        if not parser.can_fetch(AGENT, URL):
            return False, 'robots-disallowed'
        payload = fetch(opener, URL, 'application/rss+xml, application/xml, text/xml')
        # Do not process DTDs or entities from an external source.
        if b'<!doctype' in payload.lower() or b'<!entity' in payload.lower():
            return False, 'xml-dtd-rejected'
        root = ET.fromstring(payload)
        if root.tag != 'rss' or root.find('channel') is None:
            return False, 'not-rss'
        items = root.findall('./channel/item')
        if not items or not any(item.findtext('title') and item.findtext('link') for item in items):
            return False, 'empty-or-invalid-feed'
        return True, 'rss-validated'
    except urllib.error.HTTPError as exc:
        # 3xx is reported, never followed; 403/429 are not bypassed or retried.
        return False, f'http-{exc.code}' if 100 <= exc.code <= 599 else 'http-error'
    except ssl.SSLError:
        return False, 'tls-error'
    except urllib.error.URLError as exc:
        return False, 'tls-error' if isinstance(exc.reason, ssl.SSLError) else 'network-error'
    except (TimeoutError, OSError):
        return False, 'network-error'
    except UnicodeDecodeError:
        return False, 'robots-invalid-encoding'
    except ET.ParseError:
        return False, 'invalid-xml'
    except ValueError as exc:
        return False, 'response-too-large' if str(exc) == 'response-too-large' else 'invalid-response'


def main():
    if sys.argv[1:] != ['--confirm-read-only']:
        print('Use --confirm-read-only for an HTTPS check; no files will be written.')
        return 2
    ok, category = check()
    if ok:
        print('HTTPS probe: rss-validated. No files were written or published.')
        return 0
    print(f'::error::HTTPS probe failed: {category}. No files were written or published.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
