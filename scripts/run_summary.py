"""Append fixed, non-secret status messages to the GitHub Actions job summary."""
import os
import sys


def report(message):
    print(message)
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        try:
            with open(path, 'a', encoding='utf-8') as summary:
                summary.write(message + '\n\n')
        except OSError:
            # A missing summary must never turn a failed or successful publication
            # into a different result, or hide the message from the normal log.
            print('::warning::Could not write Actions job summary.', file=sys.stderr)
