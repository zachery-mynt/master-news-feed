# Master News Feed Publisher

Merges 511 Google Alerts RSS feeds into one auto-updating master feed, hosted free on
GitHub and served at a public URL that Zapier can poll to post news into Slack.

## What's in here

- `merge_feeds.py` — fetches all feeds, dedupes, sorts newest-first, tags each item with its source. Stdlib only.
- `feed_urls.txt` — your 511 Google Alerts feed URLs (one per line). Edit this to add/remove sources.
- `master_feed.xml` — the merged output. Regenerated automatically.
- `.github/workflows/merge.yml` — GitHub Action that re-runs the merge every hour and commits the result.

---

## Part 1 — Put this on GitHub (one-time, ~5 min)

1. Go to github.com and create a **new public repository** — e.g. `master-news-feed`.
   (It must be public for the raw feed URL to be reachable by Zapier.)
2. Upload these files, keeping the folder structure (the `.github/workflows/` folder matters).
   Easiest: on the new repo page, click **"uploading an existing file"** and drag everything in.
   The `.github` folder is hidden in Finder — if drag-and-drop skips it, create the file manually:
   in GitHub click **Add file → Create new file**, name it `.github/workflows/merge.yml`, and paste
   the contents of the local `merge.yml`.
3. Commit. Go to the **Actions** tab and, if prompted, click **"I understand my workflows, enable them."**
4. Open the **"Merge Google Alerts feeds"** workflow and click **Run workflow** once to confirm it works.
   After it finishes, `master_feed.xml` will update with a fresh timestamp.

### Your feed URL

Once pushed, your public, auto-updating feed lives at:

```
https://raw.githubusercontent.com/<YOUR-USERNAME>/<YOUR-REPO>/main/master_feed.xml
```

Replace `<YOUR-USERNAME>` and `<YOUR-REPO>`. (If your default branch is `master` instead of
`main`, use that.) Open it in a browser to confirm it loads the XML.

The hourly schedule keeps it current. To change the cadence, edit the `cron` line in `merge.yml`
(e.g. `0 */4 * * *` for every 4 hours). Note: GitHub disables scheduled workflows after 60 days of
no repo activity — just re-enable from the Actions tab if that ever happens.

---

## Part 2 — Wire it into Slack with Zapier

1. In Zapier, create a new Zap.
2. **Trigger:** "RSS by Zapier" → event **"New Item in Feed"** → paste your `raw.githubusercontent.com`
   feed URL from above. Test it; you should see a recent article.
3. *(Optional but recommended)* Add a **Filter by Zapier** step to only post items that match
   categories you care about — e.g. only continue if the title or description **contains**
   `raises` OR `funding` OR `Series` OR `launches` OR `appoints`. (Zapier filters take one condition
   per row with OR groups.)
4. **Action:** "Slack" → **"Send Channel Message"** → choose your channel and build the message, e.g.:

   ```
   📰 {{title}}
   {{source}} · {{date_published}}
   {{link}}
   ```

5. Turn the Zap on. New articles will now flow into Slack automatically.

> Tip: if you want different categories routed to different channels, duplicate the Zap and change
> the Filter keywords + target channel in each copy.

---

## Maintaining your feeds

- **Add/remove sources:** edit `feed_urls.txt` (one feed URL per line) and commit. The next run picks it up.
- **Noisy alerts:** a few Google Alerts queries catch false matches (e.g. "Woman Within" matching
  "woman in"). Tighten those queries in Google Alerts (exact-phrase quotes) and refresh their URLs.
- **History:** each Google Alerts feed only holds its ~20 most recent items, so the master feed is a
  rolling recent window, not a full archive. Running on a schedule is what accumulates coverage over time.
