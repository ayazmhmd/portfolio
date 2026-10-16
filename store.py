"""Content and file storage.

Two backends, chosen automatically:

* Local (default): files are read from and written to this folder. Use this on your
  own computer or on a host with a persistent disk (e.g. PythonAnywhere).
* GitHub (when GITHUB_TOKEN and GITHUB_REPO are set): used on Vercel, whose disk is
  read-only. Every save from the admin panel becomes one commit to the repository;
  Vercel then redeploys the site automatically (about a minute).
"""
import base64
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

import requests
import yaml

BASE = Path(__file__).resolve().parent
CONTENT_PATH = "content.yaml"
INSTANCE = BASE / "instance"
PUBLIC_FILES = "static/files"
PRIVATE_FILES = "private"
PROJECTS = "static/projects"
IMG = "static/img"

_lock = threading.Lock()


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(str, lambda d, s: d.represent_scalar(
    "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def dump_yaml(obj):
    return yaml.dump(obj, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60].strip("-") or "item"


# ------------------------------------------------------------------ backends
class LocalBackend:
    name = "local"
    live_note = "Changes are live immediately."

    def read_bytes(self, path):
        p = BASE / path
        return p.read_bytes() if p.is_file() else None

    def commit(self, changes, message):
        """changes: {relative_path: bytes or None (delete)}"""
        with _lock:
            if CONTENT_PATH in changes and (BASE / CONTENT_PATH).exists():
                bk = INSTANCE / "backups"
                bk.mkdir(parents=True, exist_ok=True)
                shutil.copy2(BASE / CONTENT_PATH, bk / f"content-{datetime.now():%Y%m%d-%H%M%S-%f}.yaml")
                for old in sorted(bk.glob("content-*.yaml"))[:-40]:
                    old.unlink()
            for path, data in changes.items():
                target = (BASE / path).resolve()
                if BASE not in target.parents:
                    raise ValueError(f"refusing to write outside the site: {path}")
                if data is None:
                    if target.exists():
                        trash = INSTANCE / "trash"
                        trash.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(target), trash / f"{datetime.now():%Y%m%d%H%M%S}-{target.name}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_name(target.name + ".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, target)


class GitHubBackend:
    name = "github"
    live_note = "Saved to GitHub. The public site updates after Vercel redeploys (about a minute)."

    def __init__(self, token, repo, branch="main"):
        self.repo, self.branch = repo, branch
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})
        self.api = f"https://api.github.com/repos/{repo}"

    def _req(self, method, url, **kw):
        r = self.s.request(method, url, timeout=25, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"GitHub API {method} {url.split('/repos/')[-1]} -> {r.status_code}: {r.text[:300]}")
        return r

    def read_bytes(self, path):
        r = self.s.get(f"{self.api}/contents/{path}", params={"ref": self.branch},
                       headers={"Accept": "application/vnd.github.raw"}, timeout=25)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"GitHub read {path} -> {r.status_code}")
        return r.content

    def commit(self, changes, message):
        for attempt in range(2):
            ref = self._req("GET", f"{self.api}/git/ref/heads/{self.branch}").json()
            head = ref["object"]["sha"]
            base_tree = self._req("GET", f"{self.api}/git/commits/{head}").json()["tree"]["sha"]
            tree = []
            for path, data in changes.items():
                if data is None:
                    tree.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                    continue
                blob = self._req("POST", f"{self.api}/git/blobs", json={
                    "content": base64.b64encode(data).decode(), "encoding": "base64"}).json()
                tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            new_tree = self._req("POST", f"{self.api}/git/trees", json={"base_tree": base_tree, "tree": tree}).json()
            commit = self._req("POST", f"{self.api}/git/commits", json={
                "message": message, "tree": new_tree["sha"], "parents": [head]}).json()
            r = self.s.patch(f"{self.api}/git/refs/heads/{self.branch}", json={"sha": commit["sha"]}, timeout=25)
            if r.status_code < 400:
                return
            if attempt == 1:
                raise RuntimeError(f"GitHub update ref -> {r.status_code}: {r.text[:200]}")

    # contact messages become issues, so GitHub e-mails you and no redeploy is triggered
    def create_issue(self, title, body):
        self._req("POST", f"{self.api}/issues", json={"title": title, "body": body, "labels": ["contact"]})

    def list_issues(self):
        r = self._req("GET", f"{self.api}/issues", params={"labels": "contact", "state": "all", "per_page": 100})
        return r.json()


def _backend():
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO")
    if tok and repo:
        return GitHubBackend(tok, repo, os.environ.get("GITHUB_BRANCH", "main"))
    return LocalBackend()


backend = _backend()


# ------------------------------------------------------------------ content
DEFAULTS = {"projects": [], "news": [], "documents": [], "references": [], "share_links": []}


def _parse(text):
    data = yaml.safe_load(text) or {}
    for k, v in DEFAULTS.items():
        if data.get(k) is None:
            data[k] = list(v)
    return data


def load_content(fresh=False):
    """Public pages read the deployed file. The admin passes fresh=True so that, on
    GitHub storage, it sees edits that have not been redeployed yet."""
    if fresh and backend.name == "github":
        raw = backend.read_bytes(CONTENT_PATH)
        if raw is not None:
            return _parse(raw.decode("utf-8"))
    return _parse((BASE / CONTENT_PATH).read_text(encoding="utf-8"))


def save_content(data, message="Update site content", files=None):
    changes = dict(files or {})
    changes[CONTENT_PATH] = ("# Site content. Edit from /admin or by hand.\n" + dump_yaml(data)).encode("utf-8")
    backend.commit(changes, message)


def read_file(path):
    """Read a site file: the deployed copy first, then storage (for fresh uploads)."""
    p = BASE / path
    if p.is_file():
        return p.read_bytes()
    if backend.name == "github":
        return backend.read_bytes(path)
    return None
