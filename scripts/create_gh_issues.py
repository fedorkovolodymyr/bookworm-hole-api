#!/usr/bin/env python3
"""Parse BACKEND_ISSUES.md and create GitHub issues via gh CLI."""
import re
import subprocess
import sys
import json

ISSUES_FILE = "BACKEND_ISSUES.md"

LABELS_TO_CREATE = [
    # Priority
    ("priority:P0", "Blocking — must fix before anything else", "b60205"),
    ("priority:P1", "Core feature — required for MVP", "d93f0b"),
    ("priority:P2", "Deferrable — nice but not blocking", "e4e669"),
    ("priority:P3", "Nice-to-have", "0e8a16"),
    # Type
    ("type:infra", "Infrastructure / config / tooling", "5319e7"),
    ("type:feature", "New feature", "1d76db"),
    ("type:task", "Non-feature task", "0075ca"),
    ("type:test", "Tests", "006b75"),
    ("type:chore", "Chore / maintenance", "e4e669"),
    # Status
    ("status:todo", "Not started", "cccccc"),
    ("status:in-progress", "In progress", "fbca04"),
    ("status:done", "Done", "0e8a16"),
    # Epics
    ("epic:infra", "Epic 1 – Infrastructure", "c5def5"),
    ("epic:books", "Epic 2 – Books", "c5def5"),
    ("epic:search", "Epic 3 – Search", "c5def5"),
    ("epic:auth", "Epic 4 – Auth", "c5def5"),
    ("epic:collections", "Epic 5 – Collections", "c5def5"),
    ("epic:status", "Epic 6 – Reading Status", "c5def5"),
    ("epic:reviews", "Epic 7 – Reviews", "c5def5"),
    ("epic:sessions", "Epic 8 – Reading Sessions", "c5def5"),
    ("epic:social", "Epic 9 – Social", "c5def5"),
    ("epic:external", "Epic 10 – External APIs", "c5def5"),
    ("epic:moderation", "Epic 11 – Moderation", "c5def5"),
    ("epic:import-export", "Epic 12 – Import/Export", "c5def5"),
    ("epic:gdrive", "Epic 13 – Google Drive", "c5def5"),
    ("epic:seed", "Epic 14 – Seed Data", "c5def5"),
    ("epic:ai", "Epic 15 – AI", "c5def5"),
    ("epic:admin", "Epic 16 – Admin", "c5def5"),
    ("epic:tests", "Epic 17 – Tests", "c5def5"),
]


def create_labels():
    print("Creating labels...")
    existing = subprocess.run(
        ["gh", "label", "list", "--json", "name", "--limit", "200"],
        capture_output=True, text=True
    ).stdout
    existing_names = {label["name"] for label in json.loads(existing)} if existing.strip() else set()

    for name, desc, color in LABELS_TO_CREATE:
        if name in existing_names:
            print(f"  skip (exists): {name}")
            continue
        r = subprocess.run(
            ["gh", "label", "create", name, "--description", desc, "--color", color],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print(f"  created: {name}")
        else:
            print(f"  FAILED {name}: {r.stderr.strip()}")


def parse_issues(path):
    with open(path) as f:
        content = f.read()

    # Split on issue headers
    pattern = r'(### \[ISSUE-\d+\].*?)(?=### \[ISSUE-\d+\]|\Z)'
    blocks = re.findall(pattern, content, re.DOTALL)

    issues = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Title line
        title_match = re.match(r'### \[ISSUE-(\d+)\] (.+)', block)
        if not title_match:
            continue
        num = title_match.group(1)
        title = title_match.group(2).strip()

        # Fields
        def field(key):
            m = re.search(rf'\*\*{key}:\*\*\s*(.+)', block)
            return m.group(1).strip() if m else ""

        priority = field("Priority")
        labels_raw = field("Labels")

        # Parse label slugs
        label_slugs = re.findall(r'`([^`]+)`', labels_raw)
        # Map to our label scheme
        gh_labels = []
        for slug in label_slugs:
            if slug.startswith("epic:") or slug.startswith("type:") or slug.startswith("status:"):
                gh_labels.append(slug)
        if priority:
            gh_labels.append(f"priority:{priority}")

        # Body: everything after the title line
        body_lines = block.split('\n')[1:]
        body = '\n'.join(body_lines).strip()
        # Clean trailing ---
        body = re.sub(r'\n---\s*$', '', body).strip()

        issues.append({
            "num": num,
            "title": f"[ISSUE-{num}] {title}",
            "labels": gh_labels,
            "body": body,
        })

    return issues


def create_issue(issue):
    cmd = ["gh", "issue", "create",
           "--title", issue["title"],
           "--body", issue["body"]]
    for label in issue["labels"]:
        cmd += ["--label", label]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        url = r.stdout.strip()
        print(f"  created ISSUE-{issue['num']}: {url}")
    else:
        print(f"  FAILED ISSUE-{issue['num']}: {r.stderr.strip()}")


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

    create_labels()

    issues = parse_issues(ISSUES_FILE)
    print(f"\nFound {len(issues)} issues. Creating {start}–{end}...\n")

    for issue in issues:
        n = int(issue["num"])
        if n < start or n > end:
            continue
        create_issue(issue)

    print("\nDone.")


if __name__ == "__main__":
    main()
