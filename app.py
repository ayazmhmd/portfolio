"""Ayaz Mehmood: research portfolio (Flask).

    pip install -r requirements.txt
    python app.py           -> http://localhost:5000      (admin: /admin)
On Vercel the same app runs serverless; see DEPLOY.md.
"""
import io
import json
import mimetypes
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

import markdown as md
from flask import (Flask, abort, flash, g, redirect, render_template, request, send_file,
                   session, url_for)
from markupsafe import Markup, escape

import store
from admin import bp as admin_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("VERCEL"))
app.register_blueprint(admin_bp)

STATUS = {
    "published": "published", "preprint": "preprint", "shared_task": "shared task",
    "under_review": "under review", "submitted": "submitted",
    "ready": "ready for submission", "in_progress": "in progress",
}
GROUPS = [
    ("Under review and in preparation", ("under_review", "submitted", "ready")),
    ("Publications and preprints", ("published", "preprint", "shared_task")),
    ("Ongoing work", ("in_progress",)),
]
LINK_LABELS = {"arxiv": "arXiv", "pdf": "PDF", "doi": "DOI", "code": "code", "kaggle": "Kaggle",
               "slides": "slides", "poster": "poster", "video": "video"}
DOC_KINDS = {"cv": "CV", "transcript": "Transcript", "degree": "Degree", "letter": "Letter",
             "statement": "Statement", "proposal": "Proposal", "certificate": "Certificate", "other": "Document"}


def site():
    if "site" not in g:
        g.site = store.load_content()
    return g.site


def active_share():
    """The share link this visitor opened, if it is still active."""
    tok = session.get("share")
    if not tok:
        return None
    return next((s for s in site().get("share_links", []) if s.get("token") == tok and s.get("active", True)), None)


def can_see(doc):
    return doc.get("visibility", "public") == "public" or session.get("admin") or active_share() is not None


@app.context_processor
def inject_globals():
    return {"site": site(), "STATUS": STATUS, "GROUPS": GROUPS, "LINK_LABELS": LINK_LABELS,
            "DOC_KINDS": DOC_KINDS, "year": datetime.now().year, "is_admin": session.get("admin", False),
            "share": active_share(), "can_see": can_see, "cv_href": cv_href()}


def cv_href():
    doc = next((d for d in site().get("documents", []) if d.get("kind") == "cv" and d.get("visibility") == "public"), None)
    if doc:
        return url_for("document_file", doc_id=doc["id"], name=doc["file"])
    pdf = site().get("profile", {}).get("cv_pdf")
    return url_for("static", filename=pdf) if pdf else url_for("documents")


@app.template_filter("asset")
def asset(filename, slug):
    return url_for("static", filename=f"projects/{slug}/{filename}")


@app.template_filter("paras")
def paras(text):
    if not text:
        return ""
    out = []
    for block in re.split(r"\n\s*\n", str(text).strip()):
        html = str(escape(block)).replace("\n", "<br>")
        html = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', html)
        out.append(f"<p>{html}</p>")
    return Markup("\n".join(out))


@app.template_filter("markdown")
def markdown_filter(text):
    if not text:
        return ""
    # escape raw HTML first: content is Markdown only
    html = md.markdown(str(escape(text)).replace("&gt;", ">"), extensions=["tables", "sane_lists"])
    return Markup(html)


@app.template_filter("me")
def highlight_me(authors):
    html = str(escape(authors or ""))
    return Markup(re.sub(r"(A\. Mehmood|Ayaz Mehmood)", r"<b>\1</b>", html))


def project_tables(p):
    """Support both the old single `results` table and the newer list of `tables`."""
    tables = list(p.get("tables") or [])
    if not tables and p.get("results", {}).get("rows"):
        tables = [p["results"]]
    return tables


app.jinja_env.globals["project_tables"] = project_tables


# ------------------------------------------------------------------ pages
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/research")
def research():
    return render_template("research.html")


@app.route("/research/<slug>")
def project(slug):
    projects = site()["projects"]
    idx = next((i for i, p in enumerate(projects) if p.get("slug") == slug), None)
    if idx is None:
        abort(404)
    p = projects[idx]
    groups = {}
    for i, f in enumerate(p.get("figures") or []):
        groups.setdefault(f.get("group") or "Figures", []).append((i + 1, f))
    return render_template("project.html", p=p, fig_groups=groups,
                           prev_p=projects[idx - 1] if idx > 0 else None,
                           next_p=projects[idx + 1] if idx + 1 < len(projects) else None)


@app.route("/cv")
def cv():
    return render_template("cv.html")


@app.route("/about")
def about_redirect():
    return redirect(url_for("cv"), 301)


@app.route("/research-interests")
def interests():
    return render_template("interests.html")


@app.route("/research-direction")
@app.route("/future-work")
@app.route("/proposal")
def old_interest_pages():
    return redirect(url_for("interests"), 301)


# ------------------------------------------------------------------ documents
@app.route("/documents")
def documents():
    return render_template("documents.html")


@app.route("/s/<token>")
def open_share(token):
    if any(s.get("token") == token and s.get("active", True) for s in site().get("share_links", [])):
        session["share"] = token
        session.permanent = True
        return redirect(url_for("documents"))
    abort(404)


@app.route("/documents/<doc_id>/<path:name>")
@app.route("/documents/<doc_id>")
def document_file(doc_id, name=None):
    doc = next((d for d in site().get("documents", []) if d.get("id") == doc_id), None)
    if not doc:
        abort(404)
    if not can_see(doc):
        flash("This document is shared on request. Please get in touch and I'll send you a link.", "error")
        return redirect(url_for("documents"))
    folder = store.PUBLIC_FILES if doc.get("visibility", "public") == "public" else store.PRIVATE_FILES
    data = store.read_file(f"{folder}/{doc['file']}")
    if data is None:
        abort(404)
    mime = mimetypes.guess_type(doc["file"])[0] or "application/octet-stream"
    resp = send_file(io.BytesIO(data), mimetype=mime, download_name=doc["file"],
                     as_attachment=request.args.get("download") == "1")
    if doc.get("visibility") != "public":
        resp.headers["Cache-Control"] = "private, no-store"
        resp.headers["X-Robots-Tag"] = "noindex"
    return resp


# ------------------------------------------------------------------ contact
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        if request.form.get("website"):  # honeypot
            return redirect(url_for("contact"))
        msg = {k: request.form.get(k, "").strip()[:4000] for k in ("name", "email", "affiliation", "kind", "message")}
        if not msg["name"] or "@" not in msg["email"] or not msg["message"]:
            flash("Please fill in your name, email and a message.", "error")
            return render_template("contact.html", form=msg), 400
        msg["received"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            save_message(msg)
        except Exception as e:  # never lose the visitor's message silently
            app.logger.error("Could not store message: %s", e)
            flash(f"Sorry, the form failed. Please email me directly at {site()['contact']['email']}.", "error")
            return render_template("contact.html", form=msg), 500
        flash("Thanks, your message was sent. I'll reply by email.", "ok")
        return redirect(url_for("contact"))
    return render_template("contact.html", form={})


def save_message(msg):
    sent = False
    if store.backend.name == "github":
        body = "\n".join(f"**{k}:** {v}" for k, v in msg.items() if k != "message") + "\n\n---\n\n" + msg["message"]
        store.backend.create_issue(f"[{msg['kind'] or 'Message'}] {msg['name']} ({msg['affiliation'] or msg['email']})", body)
        sent = True
    else:
        store.INSTANCE.mkdir(exist_ok=True)
        with open(store.INSTANCE / "messages.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sent = True
    if send_email(msg):
        sent = True
    if not sent:
        raise RuntimeError("no message channel configured")


def send_email(msg):
    host, user, pw = (os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))
    if not (host and user and pw):
        return False
    try:
        em = EmailMessage()
        em["Subject"] = f"[Website] {msg['kind'] or 'Message'} from {msg['name']}"
        em["From"] = user
        em["To"] = site()["contact"]["email"]
        em["Reply-To"] = msg["email"]
        em.set_content("\n".join(f"{k}: {v}" for k, v in msg.items()))
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=10) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(em)
        return True
    except Exception as e:
        app.logger.warning("Email notification failed: %s", e)
        return False


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_big(_):
    flash("That upload is too large.", "error")
    return redirect(request.referrer or url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
