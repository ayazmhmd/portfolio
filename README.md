# Ayaz Mehmood: research portfolio (Flask)

Pages: home · research (one page per paper, with figures that enlarge on click, result
tables and key numbers) · future work · proposal · CV · documents (public CV; private
transcripts and degree behind share links) · contact.

- **Put it online:** see [DEPLOY.md](DEPLOY.md) (Vercel + GitHub, free).
- **Run locally:** `pip install -r requirements.txt && python app.py` → http://localhost:5000
- **Admin panel:** `/admin` (password from `ADMIN_PASSWORD`, default `change-me` locally).

## Layout
| Path | What |
|---|---|
| `content.yaml` | All text: profile, papers, figures, tables, documents, references, news |
| `static/projects/<slug>/` | Figures and files for each paper |
| `static/files/` | Public documents (CV) |
| `private/` | Private documents (served only via share links or to the admin) |
| `app.py`, `admin.py`, `store.py` | Site, admin panel, storage (local disk or GitHub) |
