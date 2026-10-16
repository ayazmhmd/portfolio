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
| `static/notebook/` | The research-summary notebook (HTML + .ipynb) linked from the site |
| `notebook/` | Notebook source: cropping re-implementation, result data, figure scripts |
| `app.py`, `admin.py`, `store.py` | Site, admin panel, storage (local disk or GitHub) |

## The notebook
`notebook/mammography_research_summary.ipynb` runs anywhere with numpy, pandas, matplotlib
and opencv. To publish it on Kaggle: create a new notebook, upload the `.ipynb`, add a
dataset with the two images in `notebook/data/` (named `mammo-samples`), run all, and
then paste the Kaggle link into Admin → Other pages → Notebook link.
To rebuild it: `cd notebook && python build_notebook.py && jupyter nbconvert --execute --inplace mammography_research_summary.ipynb`.
