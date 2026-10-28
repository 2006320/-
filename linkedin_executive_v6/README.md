# LinkedIn Executive V6 — PostgreSQL shared dedup

V6 replaces the V5 SQLite storage with **one shared PostgreSQL database**. Multiple Streamlit web instances and background workers use the same `DATABASE_URL`; `dedup_pool.url` is a primary key and atomic `INSERT ... ON CONFLICT DO NOTHING` prevents duplicate enrollment even with concurrent requests. Worker claims use `FOR UPDATE SKIP LOCKED` to prevent simultaneous claims.

## Deploy

1. Provision PostgreSQL with persistent storage and TLS (e.g. managed Postgres). Obtain the connection URI; keep it secret. **Do not expose PostgreSQL directly to the public internet**.
2. Install: `pip install -r requirements.txt`.
3. Set environment variable `DATABASE_URL` in both the web service and worker to the **same** URI. Example `postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require` (replace all placeholders). For an internet-facing app also set `APP_PASSWORD` to a strong password.
4. Initialize and migrate historical text links **once**: `python seed_history.py`. The import is idempotent; rerunning it does not create duplicates. The bundled seed contains the three historical text files used in V5.
5. Web service: `streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-8501}` (or configure the host's port).
6. Separate long-running worker: `python worker.py`. For multiple workers, run separate replicas with the same DATABASE_URL. For deployments that sleep/stop workers, queued jobs will wait until a worker is available.

**Important:** Streamlit Community Cloud alone does not provide an always-on worker or guarantee persistent task execution. Use a host supporting a web service + a long-running worker + managed Postgres. Hosting may incur charges. This package is not deployed for you.

## Cross-chat use

Other ChatGPT windows do not automatically share their chat transcripts with this app. Export TXT/CSV links from each chat and upload through the "历史去重池" tab, or point multiple instances of this app to the same DATABASE_URL. Do not copy the database to each worker. The shared DB is the single source of truth.

## Concurrency, semantics and cautions

- A URL is reserved in `dedup_pool` **on admission to the task**, not after success. Failed/cancelled tasks therefore still count as seen. This is deliberate global never-research-again behavior; add a separate recheck policy if needed.
- Duplicate detection is URL-based, not guaranteed person-identity matching. It normalizes LinkedIn profile URLs and strips query strings; it does not identify aliases for the same person.
- PostgreSQL transactions make simultaneous task submissions safe. Worker claims use row locking; a crashed worker's item can be requeued after the stale timeout (`recover_stale`, default 600s). A very long processing task can exceed the timeout and be retried, so results must be treated as at-least-once processing.
- Pausing stops new claims; an item already being processed may finish. No authenticated per-user tenancy is implemented; all authorized users see the same task history. Use a private deployment, HTTPS, and `APP_PASSWORD` or stronger gateway authentication.
- Only access publicly permitted web content and authorized profile data. No login bypass or anti-bot circumvention is implemented. Evidence-based filters remain heuristic and need review.
- Back up the managed PostgreSQL database regularly; do not store secrets in GitHub.

## Checks

`python -m compileall -q .` and `python -m unittest discover -s tests -v` perform syntax and offline canonicalization tests. Integration against a real PostgreSQL server must be performed after deployment.

## V7 Keenable/Keenable public search integration

- ChatGPT Keenable plugin results can be imported as JSON via the new **Keenable 搜索导入** tab.
- Accepted result shapes: `[{"url":"https://example.org","title":"...","snippet":"..."}]` or `{"results":[...]}` (also `items`/`pages` and nested `data.results`).
- Results go through the existing PostgreSQL global dedup and task queue.
- Search snippets are discovery hints only, never verified career evidence. Worker fetches public page separately, respecting access restrictions.
- This is **not** an automatic direct integration with ChatGPT's private plugin transport. A server-side integration requires an independently authorized Keenable API, credentials, and documented terms. No free unlimited API entitlement is assumed.
