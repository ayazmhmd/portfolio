# Putting the site live on Vercel (about 20 minutes, free)

How it works: your site's files live in a **private GitHub repository**. Vercel runs the
site from that repository. When you save something in the admin panel, the change is
committed to GitHub, and Vercel automatically redeploys it. The public site shows the
change about a minute later.

You need a free GitHub account and a free Vercel account (sign up for Vercel with GitHub).

---

## 1. Put the code on GitHub

1. Go to https://github.com/new
   - Repository name: `portfolio`
   - Choose **Private**. This matters: your private documents (transcripts, degree) are
     stored in the repository.
   - Click **Create repository**.
2. On the new repository page, click **uploading an existing file**. Unzip
   `phd-portfolio.zip` on your computer, open the `phd-portfolio` folder, select
   **everything inside it** (not the folder itself) and drag it into the browser.
   Click **Commit changes**.

   (If you use git instead:
   `cd phd-portfolio && git init && git add . && git commit -m "Portfolio" && git branch -M main && git remote add origin https://github.com/<you>/portfolio.git && git push -u origin main`)

## 2. Create a GitHub token for the admin panel

The admin panel needs permission to save into this one repository.

1. Go to https://github.com/settings/personal-access-tokens/new (fine-grained token).
2. Token name: `portfolio admin`. Expiration: 1 year (set a reminder to renew it).
3. Repository access: **Only select repositories** → `portfolio`.
4. Permissions → Repository permissions:
   - **Contents: Read and write**
   - **Issues: Read and write** (contact-form messages are saved as issues)
5. Click **Generate token** and copy it (it starts with `github_pat_`). You see it only once.

## 3. Deploy on Vercel

1. Go to https://vercel.com/new and import the `portfolio` repository.
2. Framework preset: **Other**. Leave the build settings empty; `vercel.json` handles it.
3. Open **Environment Variables** and add:

| Name | Value |
|---|---|
| `ADMIN_PASSWORD` | a strong password for /admin |
| `SECRET_KEY` | any long random text (e.g. 40 random letters and digits) |
| `GITHUB_TOKEN` | the token from step 2 |
| `GITHUB_REPO` | `your-github-username/portfolio` |
| `GITHUB_BRANCH` | `main` |

4. Click **Deploy**. After about a minute you get a link like `https://portfolio-xxxx.vercel.app`.
5. Optional: in Vercel → Project → Settings → Domains, rename it to something like
   `ayaz-mehmood.vercel.app`, or connect your own domain.

## 4. Check it works

- Open the site and click through Research, the two mammography papers, and Documents.
- Go to `/admin`, log in, and add a test news item. The admin panel shows it immediately.
  The public home page shows it after Vercel redeploys (watch the Deployments tab;
  about a minute). Then delete the test item.
- Send yourself a message through the Contact page. It appears as an issue in your
  GitHub repository, and GitHub emails you.

## Using it day to day

| I want to… | Where |
|---|---|
| Add a paper or project, with figures, tables and key numbers | Admin → + New project |
| Add figures to a paper (click-to-enlarge, with details text) | Admin → click the paper → Figures |
| Upload a motivation letter, certificate or new CV | Admin → Documents → Add a document |
| Make a document public or private | Admin → Documents → tick or untick **Public** |
| Give a supervisor access to transcripts, degree and reference emails | Admin → Documents → Private links → **Create link**, then paste the link into your email |
| Edit references, education, research interests, skills | Admin → Other pages |
| Read contact-form messages | Admin → Messages (or the Issues tab on GitHub) |

### Limits to know about
- **Uploads up to about 4 MB per save** (a Vercel limit). Large images are shrunk
  automatically. For a bigger PDF, upload it directly on GitHub (drag it into the
  `private/` or `static/files/` folder), then add it in the admin panel.
- Private links are unguessable, but anyone who has a link can open the private
  documents, so give each person their own link and switch it off when it's no longer needed.
- Changes appear on the public site after the redeploy, about a minute after saving.

## Running it on your own computer

```
pip install -r requirements.txt
python app.py                 # http://localhost:5000, admin password "change-me"
```
Without the GitHub variables, everything is saved directly in the folder.
