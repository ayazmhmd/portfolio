"""Admin panel: projects (figures, results, files), documents, share links, news,
profile and the other pages. Log in at /admin with ADMIN_PASSWORD."""
import csv
import hmac
import io
import json
import os
import secrets
from datetime import datetime

import yaml
from flask import (Blueprint, Response, abort, flash, redirect, render_template, request,
                   session, url_for)
from PIL import Image
from werkzeug.utils import secure_filename

import store
from store import dump_yaml, slugify

bp = Blueprint("admin", __name__, url_prefix="/admin")

IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
DOC_EXT = {"pdf", "pptx", "ppt", "docx", "doc", "zip", "csv", "xlsx", "ipynb", "txt", "html", "mp4"}
LINK_KEYS = ["arxiv", "pdf", "doi", "code", "kaggle", "slides", "poster", "video"]
STATUSES = ["under_review", "submitted", "ready", "published", "preprint", "shared_task", "in_progress"]
DIAGRAMS = ["", "mammo", "lora", "risk"]
DOC_KINDS = ["cv", "transcript", "degree", "letter", "statement", "proposal", "certificate", "other"]
NEW_FIG_SLOTS, NEW_DOC_SLOTS = 4, 2
MAX_IMAGE_SIDE = 2400
YAML_SECTIONS = {
    "education": "Education",
    "experience": "Experience (research & industry)",
    "references": "References",
    "other_projects": "Other projects",
    "research_interests": "Research interests page (areas, proposed topics)",
    "skills": "Skills",
}
DEFAULT_PASSWORD = "change-me"


def admin_password():
    return os.environ.get("ADMIN_PASSWORD", DEFAULT_PASSWORD)


# ------------------------------------------------------------------ guard
@bp.before_request
def guard():
    if request.endpoint == "admin.login":
        return None
    if not session.get("admin"):
        return redirect(url_for("admin.login", next=request.path))
    if request.method == "POST" and not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
        abort(400, "Session expired, please reload the page.")
    return None


@bp.context_processor
def admin_ctx():
    return {"csrf": session.get("csrf", ""), "weak_password": admin_password() == DEFAULT_PASSWORD,
            "YAML_SECTIONS": YAML_SECTIONS, "storage": store.backend}


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        on_vercel = bool(os.environ.get("VERCEL"))
        if on_vercel and admin_password() == DEFAULT_PASSWORD:
            flash("Set ADMIN_PASSWORD in Vercel before logging in.", "error")
        elif hmac.compare_digest(request.form.get("password", ""), admin_password()):
            session.clear()
            session.update(admin=True, csrf=secrets.token_hex(16))
            session.permanent = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/admin") else url_for("admin.dashboard"))
        else:
            flash("Wrong password.", "error")
    return render_template("admin/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


def save(data, message, files=None):
    try:
        store.save_content(data, message, files)
        flash("Saved. " + store.backend.live_note, "ok")
        return True
    except Exception as e:
        flash(f"Could not save: {e}", "error")
        return False


# ------------------------------------------------------------------ files
def _ext(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def process_upload(fileobj, allowed, taken):
    """Return (filename, bytes) for an upload, or (None, None). Large images are
    downsized so pages stay fast and uploads fit serverless limits."""
    name = secure_filename(fileobj.filename or "")
    ext = _ext(name)
    if not name or ext not in allowed:
        flash(f"Skipped '{fileobj.filename}': allowed types are {', '.join(sorted(allowed))}.", "error")
        return None, None
    data = fileobj.read()
    if ext in {"png", "jpg", "jpeg", "webp"}:
        try:
            im = Image.open(io.BytesIO(data))
            if max(im.size) > MAX_IMAGE_SIDE:
                im.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
                buf = io.BytesIO()
                if ext in {"jpg", "jpeg"}:
                    im.convert("RGB").save(buf, "JPEG", quality=88, optimize=True)
                else:
                    im.save(buf, "PNG" if ext == "png" else "WEBP", optimize=True)
                data = buf.getvalue()
        except Exception:
            flash(f"'{name}' does not look like a valid image.", "error")
            return None, None
    stem, n, cand = name.rsplit(".", 1)[0], 1, name
    while cand in taken:
        n += 1
        cand = f"{stem}-{n}.{ext}"
    taken.add(cand)
    return cand, data


def is_wide(blob):
    """Wide images (pipelines, multi-panel charts) span the full page width."""
    try:
        w, h = Image.open(io.BytesIO(blob)).size
        return w / h > 1.9
    except Exception:
        return False


def folder_names(folder):
    p = store.BASE / folder
    return {f.name for f in p.iterdir()} if p.is_dir() else set()


@bp.route("/raw/<path:path>")
def raw(path):
    """Preview a stored file (also works before Vercel has redeployed)."""
    if not (path.startswith(("static/", "private/"))) or ".." in path:
        abort(404)
    data = store.read_file(path)
    if data is None:
        abort(404)
    import mimetypes
    return Response(data, mimetype=mimetypes.guess_type(path)[0] or "application/octet-stream")


# ------------------------------------------------------------------ helpers for forms
def find_project(data, slug):
    for i, p in enumerate(data["projects"]):
        if p.get("slug") == slug:
            return i, p
    abort(404)


def approach_to_text(steps):
    return "\n".join(f"{s.get('title', '')}: {s.get('text', '')}" if s.get("title") else s.get("text", "")
                     for s in steps or [])


def text_to_approach(text):
    steps = []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-•*").strip()
        if not line:
            continue
        t, sep, d = line.partition(":")
        steps.append({"title": t.strip(), "text": d.strip()} if sep and len(t) < 60 else {"title": "", "text": line})
    return steps


def tables_to_text(tables):
    out = []
    for t in tables or []:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(t.get("header", []))
        w.writerows(t.get("rows", []))
        out.append(f"## {t.get('caption', '')}\n{buf.getvalue().strip()}")
    return "\n\n".join(out)


def text_to_tables(text):
    tables, cur = [], None
    for block in [b for b in (text or "").replace("\r\n", "\n").split("\n\n") if b.strip()]:
        lines = block.strip().split("\n")
        caption = ""
        if lines[0].startswith("##"):
            caption, lines = lines[0].lstrip("#").strip(), lines[1:]
        rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO("\n".join(lines))) if any(c.strip() for c in r)]
        if rows:
            tables.append({"caption": caption, "header": rows[0], "rows": rows[1:]})
    return tables


def highlights_to_text(h):
    return "\n".join(f"{x.get('value', '')} | {x.get('label', '')}" for x in h or [])


def text_to_highlights(text):
    out = []
    for line in (text or "").splitlines():
        if "|" in line:
            v, l = line.split("|", 1)
            if v.strip():
                out.append({"value": v.strip(), "label": l.strip()})
    return out


def _year(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else v


def _text(f, key):
    return f.get(key, "").strip().replace("\r\n", "\n")


# ------------------------------------------------------------------ dashboard
@bp.route("/")
def dashboard():
    data = store.load_content(fresh=True)
    return render_template("admin/dashboard.html", data=data)


@bp.route("/project/<slug>/move/<direction>", methods=["POST"])
def move_project(slug, direction):
    data = store.load_content(fresh=True)
    i, _ = find_project(data, slug)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(data["projects"]):
        data["projects"][i], data["projects"][j] = data["projects"][j], data["projects"][i]
        save(data, f"Reorder projects ({slug})")
    return redirect(url_for("admin.dashboard") + "#projects")


@bp.route("/project/<slug>/delete", methods=["POST"])
def delete_project(slug):
    data = store.load_content(fresh=True)
    i, p = find_project(data, slug)
    data["projects"].pop(i)
    files = {f"{store.PROJECTS}/{slug}/{x['file']}": None for x in (p.get("figures") or []) + (p.get("documents") or [])}
    save(data, f"Delete project {slug}", files)
    return redirect(url_for("admin.dashboard"))


# ------------------------------------------------------------------ project form
@bp.route("/project/new", methods=["GET", "POST"])
@bp.route("/project/<slug>/edit", methods=["GET", "POST"])
def edit_project(slug=None):
    data = store.load_content(fresh=True)
    idx, p = (None, {}) if slug is None else find_project(data, slug)

    if request.method == "POST":
        f = request.form
        title = f.get("title", "").strip()
        if not title:
            flash("A title is required.", "error")
            return redirect(request.url)
        new_slug = p.get("slug") or slugify(f.get("slug") or title)
        if slug is None:
            taken = {q.get("slug") for q in data["projects"]}
            base, n = new_slug, 2
            while new_slug in taken:
                new_slug, n = f"{base}-{n}", n + 1
        folder = f"{store.PROJECTS}/{new_slug}"
        files = {}

        q = dict(p)
        q.pop("results", None)
        q.update({
            "slug": new_slug, "title": title,
            "authors": f.get("authors", "").strip(),
            "status": f.get("status") if f.get("status") in STATUSES else "in_progress",
            "venue": f.get("venue", "").strip(), "year": _year(f.get("year")),
            "group": f.get("group", "").strip(), "short": _text(f, "short"),
            "tags": [t.strip() for t in f.get("tags", "").split(",") if t.strip()],
            "links": {k: f.get(f"link_{k}", "").strip() for k in LINK_KEYS if f.get(f"link_{k}", "").strip()},
            "highlights": text_to_highlights(f.get("highlights")),
            "problem": _text(f, "problem"),
            "approach": text_to_approach(f.get("approach")),
            "diagram": f.get("diagram") if f.get("diagram") in DIAGRAMS else "",
            "tables": text_to_tables(f.get("tables")),
            "results_note": _text(f, "results_note"),
            "details": _text(f, "details"),
            "contribution": _text(f, "contribution"),
        })
        cit = f.get("citations", "").strip()
        if cit.isdigit():
            q["citations"] = int(cit)
        else:
            q.pop("citations", None)

        taken = {x["file"] for x in (p.get("figures") or []) + (p.get("documents") or [])} | folder_names(folder)
        figs = []
        for i, fig in enumerate(p.get("figures") or []):
            if f.get(f"fig_del_{i}"):
                files[f"{folder}/{fig['file']}"] = None
                continue
            fig = dict(fig, caption=_text(f, f"fig_caption_{i}"), description=_text(f, f"fig_desc_{i}"),
                       group=f.get(f"fig_group_{i}", "").strip(), wide=bool(f.get(f"fig_wide_{i}")))
            try:
                order = float(f.get(f"fig_order_{i}", i + 1))
            except ValueError:
                order = i + 1
            figs.append((order, i, fig))
        figs = [x[2] for x in sorted(figs, key=lambda t: (t[0], t[1]))]
        for j in range(NEW_FIG_SLOTS):
            up = request.files.get(f"newfig_file_{j}")
            if up and up.filename:
                name, blob = process_upload(up, IMAGE_EXT, taken)
                if name:
                    files[f"{folder}/{name}"] = blob
                    figs.append({"file": name, "caption": _text(f, f"newfig_caption_{j}"),
                                 "description": _text(f, f"newfig_desc_{j}"), "group": f.get(f"newfig_group_{j}", "").strip(),
                                 "wide": is_wide(blob)})
        q["figures"] = figs
        q["thumb"] = f.get("thumb", "") if f.get("thumb") in {x["file"] for x in figs} else ""

        docs = []
        for i, d in enumerate(p.get("documents") or []):
            if f.get(f"doc_del_{i}"):
                files[f"{folder}/{d['file']}"] = None
                continue
            docs.append({"file": d["file"], "label": f.get(f"doc_label_{i}", "").strip() or d["file"]})
        for j in range(NEW_DOC_SLOTS):
            up = request.files.get(f"newdoc_file_{j}")
            if up and up.filename:
                name, blob = process_upload(up, DOC_EXT | IMAGE_EXT, taken)
                if name:
                    files[f"{folder}/{name}"] = blob
                    docs.append({"file": name, "label": f.get(f"newdoc_label_{j}", "").strip() or name})
        q["documents"] = docs

        if idx is None:
            data["projects"].insert(0 if f.get("position", "top") == "top" else len(data["projects"]), q)
        else:
            data["projects"][idx] = q
        save(data, f"{'Add' if idx is None else 'Update'} project: {title[:60]}", files)
        if f.get("after") == "view":
            return redirect(url_for("project", slug=new_slug))
        return redirect(url_for("admin.edit_project", slug=new_slug))

    return render_template(
        "admin/project_form.html", p=p, is_new=slug is None, STATUSES=STATUSES, DIAGRAMS=DIAGRAMS,
        LINK_KEYS=LINK_KEYS, NEW_FIG_SLOTS=NEW_FIG_SLOTS, NEW_DOC_SLOTS=NEW_DOC_SLOTS,
        approach_text=approach_to_text(p.get("approach")),
        tables_text=tables_to_text(p.get("tables") or ([p["results"]] if p.get("results", {}).get("rows") else [])),
        highlights_text=highlights_to_text(p.get("highlights")))


# ------------------------------------------------------------------ documents
@bp.route("/documents", methods=["GET", "POST"])
def documents():
    data = store.load_content(fresh=True)
    docs = data["documents"]
    if request.method == "POST":
        f = request.form
        files = {}
        keep = []
        for i, d in enumerate(docs):
            old_folder = store.PUBLIC_FILES if d.get("visibility", "public") == "public" else store.PRIVATE_FILES
            if f.get(f"del_{i}"):
                files[f"{old_folder}/{d['file']}"] = None
                continue
            d = dict(d, title=f.get(f"title_{i}", d.get("title", "")).strip(), kind=f.get(f"kind_{i}", d.get("kind", "other")),
                     note=f.get(f"note_{i}", "").strip(), visibility="public" if f.get(f"public_{i}") else "private")
            new_folder = store.PUBLIC_FILES if d["visibility"] == "public" else store.PRIVATE_FILES
            up = request.files.get(f"replace_{i}")
            if up and up.filename:
                name, blob = process_upload(up, DOC_EXT | IMAGE_EXT, set())
                if name:
                    files[f"{old_folder}/{d['file']}"] = None
                    d["file"] = name
                    files[f"{new_folder}/{name}"] = blob
            elif new_folder != old_folder:  # visibility changed: move the file
                blob = store.read_file(f"{old_folder}/{d['file']}")
                if blob is not None:
                    files[f"{old_folder}/{d['file']}"] = None
                    files[f"{new_folder}/{d['file']}"] = blob
            try:
                order = float(f.get(f"order_{i}", i + 1))
            except ValueError:
                order = i + 1
            keep.append((order, i, d))
        docs = [x[2] for x in sorted(keep, key=lambda t: (t[0], t[1]))]

        up = request.files.get("new_file")
        if up and up.filename:
            vis = "public" if f.get("new_public") else "private"
            folder = store.PUBLIC_FILES if vis == "public" else store.PRIVATE_FILES
            taken = {d["file"] for d in docs} | folder_names(store.PUBLIC_FILES) | folder_names(store.PRIVATE_FILES)
            name, blob = process_upload(up, DOC_EXT | IMAGE_EXT, taken)
            if name:
                files[f"{folder}/{name}"] = blob
                ids = {d["id"] for d in docs}
                did, n = slugify(f.get("new_title") or name), 2
                while did in ids:
                    did, n = f"{slugify(f.get('new_title') or name)}-{n}", n + 1
                docs.append({"id": did, "title": f.get("new_title", "").strip() or name, "kind": f.get("new_kind", "other"),
                             "file": name, "visibility": vis, "note": f.get("new_note", "").strip()})
        data["documents"] = docs
        save(data, "Update documents", files)
        return redirect(url_for("admin.documents"))
    return render_template("admin/documents.html", docs=docs, DOC_KINDS=DOC_KINDS, links=data["share_links"])


@bp.route("/share", methods=["POST"])
def share():
    data = store.load_content(fresh=True)
    f = request.form
    act = f.get("action")
    if act == "create":
        data["share_links"].insert(0, {"token": secrets.token_urlsafe(12), "label": f.get("label", "").strip() or "Untitled",
                                       "created": datetime.now().strftime("%Y-%m-%d"), "active": True})
    else:
        tok = f.get("token")
        for s in list(data["share_links"]):
            if s["token"] == tok:
                if act == "toggle":
                    s["active"] = not s.get("active", True)
                elif act == "delete":
                    data["share_links"].remove(s)
    save(data, "Update share links")
    return redirect(url_for("admin.documents") + "#links")


# ------------------------------------------------------------------ profile
@bp.route("/profile", methods=["GET", "POST"])
def profile():
    data = store.load_content(fresh=True)
    if request.method == "POST":
        f = request.form
        pr, ct = data.setdefault("profile", {}), data.setdefault("contact", {})
        files = {}
        for k in ("name", "title", "location", "status", "dob", "nationality"):
            pr[k] = f.get(k, "").strip()
        pr["bio"] = [b.strip().replace("\n", " ") for b in f.get("bio", "").replace("\r\n", "\n").split("\n\n") if b.strip()]
        pr["interests"] = [t.strip() for t in f.get("interests", "").split(",") if t.strip()]
        for k in ("email", "linkedin", "github", "google_scholar", "kaggle", "orcid", "whatsapp"):
            ct[k] = f.get(k, "").strip()
        ct["show_whatsapp"] = bool(f.get("show_whatsapp"))
        ct["collaboration_note"] = f.get("collaboration_note", "").strip()
        photo = request.files.get("photo")
        if photo and photo.filename:
            name, blob = process_upload(photo, {"png", "jpg", "jpeg", "webp"}, folder_names(store.IMG))
            if name:
                files[f"{store.IMG}/{name}"] = blob
                pr["photo"] = f"img/{name}"
        if f.get("remove_photo"):
            pr["photo"] = ""
        save(data, "Update profile", files)
        return redirect(url_for("admin.profile"))
    return render_template("admin/profile.html", pr=data.get("profile", {}), ct=data.get("contact", {}))


# ------------------------------------------------------------------ news
@bp.route("/news/add", methods=["POST"])
def add_news():
    data = store.load_content(fresh=True)
    date, text = request.form.get("date", "").strip(), request.form.get("text", "").strip()
    if date and text:
        data["news"].insert(0, {"date": date, "text": text})
        save(data, "Add news item")
    return redirect(url_for("admin.dashboard") + "#news")


@bp.route("/news/<int:i>/delete", methods=["POST"])
def delete_news(i):
    data = store.load_content(fresh=True)
    if 0 <= i < len(data["news"]):
        data["news"].pop(i)
        save(data, "Remove news item")
    return redirect(url_for("admin.dashboard") + "#news")


# ------------------------------------------------------------------ YAML sections
@bp.route("/section/<key>", methods=["GET", "POST"])
def section(key):
    if key not in YAML_SECTIONS:
        abort(404)
    data = store.load_content(fresh=True)
    text = dump_yaml(data.get(key))
    if request.method == "POST":
        text = request.form.get("yaml", "").replace("\r\n", "\n")
        try:
            data[key] = yaml.safe_load(text)
        except yaml.YAMLError as e:
            flash(f"Not saved, the text has a formatting error: {e}", "error")
            return render_template("admin/section.html", key=key, text=text)
        files = {}
        save(data, f"Update {YAML_SECTIONS[key]}", files)
        return redirect(url_for("admin.section", key=key))
    return render_template("admin/section.html", key=key, text=text)


# ------------------------------------------------------------------ messages
@bp.route("/messages")
def messages():
    msgs, issues_url = [], None
    if store.backend.name == "github":
        try:
            for it in store.backend.list_issues():
                msgs.append({"title": it["title"], "body": it.get("body") or "", "url": it["html_url"],
                             "received": it["created_at"], "state": it["state"]})
            issues_url = f"https://github.com/{store.backend.repo}/issues?q=label%3Acontact"
        except Exception as e:
            flash(f"Could not load messages from GitHub: {e}", "error")
    else:
        path = store.INSTANCE / "messages.jsonl"
        if path.exists():
            for line in open(path, encoding="utf-8"):
                try:
                    m = json.loads(line)
                    msgs.append({"title": f"[{m.get('kind')}] {m.get('name')} <{m.get('email')}>",
                                 "body": (f"{m.get('affiliation')}\n\n" if m.get("affiliation") else "") + m.get("message", ""),
                                 "email": m.get("email"), "received": m.get("received", "")})
                except ValueError:
                    pass
        msgs.reverse()
    return render_template("admin/messages.html", msgs=msgs, issues_url=issues_url)
