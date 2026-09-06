#!/usr/bin/env python3
"""Fetch the full review record for a FISCO-BCOS PR into a review directory.

Usage: fetch_pr.py <pr-number> <review-dir> [api-base]

Saves pr.json, commits.json, reviews.json, comments.json (inline review
comments), issue-comments.json and codecov.md (the codecov bot report), then
prints a pin summary (title, head/base, commit/file/line counts, review-round
heads) for the start marker and known-items compilation.
"""

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API = "https://api.github.com/repos/FISCO-BCOS/FISCO-BCOS"


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    num, out_dir = sys.argv[1], sys.argv[2]
    api = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_API
    out_dir = out_dir.rstrip("/")
    os.makedirs(out_dir, exist_ok=True)

    try:
        pr = get_json(f"{api}/pulls/{num}")
        commits = get_json(f"{api}/pulls/{num}/commits")
        reviews = get_json(f"{api}/pulls/{num}/reviews")
        comments = get_json(f"{api}/pulls/{num}/comments")
        issue_comments = get_json(f"{api}/issues/{num}/comments")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit(f"PR #{num} not found at {api} (HTTP 404)")
        if e.code == 403:
            sys.exit(f"GitHub API rate limit hit (HTTP 403) — authenticate or wait. {e}")
        sys.exit(f"HTTP {e.code} fetching PR #{num}: {e.reason}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"network error fetching PR #{num}: {e}")

    save(f"{out_dir}/pr.json", pr)
    save(f"{out_dir}/commits.json", commits)
    save(f"{out_dir}/reviews.json", reviews)
    save(f"{out_dir}/comments.json", comments)
    save(f"{out_dir}/issue-comments.json", issue_comments)

    codecov = [c["body"] for c in issue_comments if c["user"]["login"] == "codecov[bot]"]
    if codecov:
        with open(f"{out_dir}/codecov.md", "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(codecov))

    round_heads = sorted({r["commit_id"] for r in reviews if r.get("commit_id")})
    print(f"PR #{num}  {pr['title']}")
    print(f"state: {pr['state']}  head: {pr['head']['sha']}  base: {pr['base']['ref']}@{pr['base']['sha']}")
    print(
        f"commits: {pr['commits']}  files: {pr['changed_files']}  "
        f"+{pr['additions']}/-{pr['deletions']}"
    )
    print(f"review rounds at: {', '.join(h[:12] for h in round_heads) or 'none (round 1)'}")
    print(f"review comments: {len(comments)}  issue comments: {len(issue_comments)}")


if __name__ == "__main__":
    main()
