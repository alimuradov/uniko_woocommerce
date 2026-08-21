# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A one-shot Python batch script that exports stock/price data from the UNIKO pharmacy accounting
system (DBF export files) and syncs it into a WordPress/WooCommerce store as products, product
variations, categories, and attributes. It is run manually (or via a scheduled task) each time a
fresh stock export is dropped in place — there is no server process, web app, or API of its own.

Two pharmacy networks are merged into one catalog:
- Primary network ("Аптека №149") — `files/ost.dbf`
- Second network ("Панацея") — `files/agasieva.dbf`, matched into the primary network's products by
  barcode (`scancod`) and remapped to specific branch names via a hardcoded table in `ru_to_lat`
  (`utils/utils.py`) — only three specific `NAMEPODR` values from the second network are merged in;
  everything else from that file is dropped.

## Commands

```bash
python3 -m venv venv && source venv/bin/activate   # (Windows: venv\Scripts\activate)
pip install -r requirements.txt

python main.py             # runs the full import (reads DBF, syncs WooCommerce)
python test_create.py      # ad-hoc manual script that POSTs two hardcoded products —
                            # hits the real WooCommerce API configured in .env, not a unit test
python test_wpcli_sync.py  # ad-hoc manual script that syncs two hardcoded test products via
                            # utils/wpcli_sync.py (SSH/WP-CLI path) — not a unit test
```

There is no test suite, linter, or CI config in this repo. Verify changes by running `main.py` (or
a narrowed-down manual script like `test_create.py`) against a real or staging WooCommerce site.

## Configuration

Copy `.env.example` to `.env` (loaded via `python-dotenv` in `utils/woocommerce.py`):

```
API_URL=              # WordPress site base URL
WOO_KEY=               # WooCommerce REST API consumer key
WOO_SECRET_KOD=        # WooCommerce REST API consumer secret
FILES_CATALOG_PATH=    # directory containing ost.dbf and agasieva.dbf
TB_BOT_TOKEN=          # optional, Telegram bot token (send_telegram_message helper)
TG_CHAT_ID=            # optional, Telegram chat id

# SSH/WP-CLI product sync (utils/wpcli_sync.py) — see "Sync products" below
SSH_HOST=               # WordPress server hostname/IP
SSH_PORT=               # default 22
SSH_USER=               # SSH user (must be able to run wp-cli against WP_PATH)
SSH_KEY_PATH=           # private key path, preferred over password auth
SSH_PASSWORD=           # fallback if no key auth
WP_PATH=                # remote absolute path to the WordPress install (wp-cli --path)
WP_CLI_BIN=             # path to the `wp` binary on the server, default "wp" (on PATH)
WP_SYNC_SCRIPT_PATH=    # remote absolute path where wpcli/sync_products.php is deployed
REMOTE_TMP_DIR=         # remote scratch dir for the per-run JSON payload, default /tmp
```

DBF files are read with `encoding='cp866'` (UNIKO exports in this legacy codepage). At the end of
a run, `main.py` posts a completion summary (execution time + freshness of each DBF file, plus the
product-sync result) to a hardcoded n8n webhook URL — the old Telegram notification path
(`send_telegram_message`) is still defined in `utils/utils.py` but currently commented out in
`main.py`.

**Deploying `wpcli/sync_products.php`:** this file is logic, not data — it is not uploaded on every
run. Copy it to the server once (`scp wpcli/sync_products.php <user>@<host>:$WP_SYNC_SCRIPT_PATH`),
and re-copy only when the script itself changes. `utils/wpcli_sync.py` only ships the per-run JSON
payload over SFTP and invokes it via `wp eval-file`.

## Architecture / data flow

`main.py` is the single entry point and runs top-to-bottom as a script (no `if __name__ ==
"__main__"` guard):

1. **Read & merge DBF data** (`get_stocks_from_dbf` / `get_stocks_seconds_dbf`): parses both DBF
   files into lists of dicts (one row per stock "lot"), then for each primary-network row, looks up
   matching barcodes in the second network and — only for the three known branch-name variants
   handled in that function — appends a synthetic extra row so that branch's stock shows up as a
   separate lot. Also collects the deduplicated universe of attribute values (brands, categories,
   MNNs, etc.) across the merged rows.
2. **Sync taxonomy** (`utils/api.py`): create any product categories that don't exist yet
   (`create_new_categories` — name comparison is case-insensitive, since category names on the site
   may have been hand-edited), create the fixed set of product attributes the project expects
   (`create_new_attributes`), then create any missing terms for each attribute
   (`get_attribute_terms` + `create_attribute_terms`).
3. **Sync products** — groups the merged stock rows by `codtmc` (product code, via
   `group_products_by_codtmc` in `utils/utils.py`) — each group becomes one WooCommerce **simple**
   product (not variable) whose per-branch stock is summed (`calculate_total_ost`) and whose price
   is the max across lots (`find_max_price`). Per-branch stock is stored as one meta_data key per
   branch name (`get_stocks_meta`), not as WooCommerce variations. Existing products (matched by
   SKU = `codtmc`) missing from the new stock file are set to `outofstock` in a first pass; the rest
   are created or updated depending on whether the SKU already exists on the site.

   There are **two independent implementations** of this step, and `main.py` calls exactly one of
   them (see the comment at that call site to switch):
   - **`utils/wpcli_sync.py`** (`sync_products_via_wpcli`, the current live path) — builds the same
     per-product data, ships it as one JSON payload over SFTP to the WordPress server, and runs
     `wpcli/sync_products.php` there via `wp eval-file` (SSH, `paramiko`). The PHP script does the
     actual create/update/outofstock work through WooCommerce's own PHP CRUD (`WC_Product_Simple`,
     `wp_set_object_terms`, `WC_Product_Attribute`, `->save()`) — no REST batching, no raw SQL writes
     (the only SQL is a read-only `SELECT` for a cheap existing-SKU lookup). This exists because the
     REST-batch path below was timing out/dropping connections on large batches; running the write
     in-process on the server removes the network round-trips that caused that. Each product is
     saved and error-isolated independently (`try/catch` per row), so one bad row can't lose an
     entire batch or corrupt other products, and a mid-run failure just leaves a partial-but-valid
     run (the next import re-diffs by SKU and catches up).
   - **`utils/api.py`** (`create_and_update_products` + `get_all_products`, REST-batch path) — the
     original implementation, kept working and unmodified as a fallback. Batches product
     create/update via `products/batch` (`batch_size = 100`); a failed batch is dropped with only a
     `time.sleep` retry, no requeue.
   - `create_variations` / `generate_variations` (variable-product + per-branch-variation approach),
     `old_create_products`, `create_products`, and `update_products` in `utils/api.py` are older/
     alternate implementations not called from either live path.

### Module map

- `utils/woocommerce.py` — builds the shared `wcapi` client (`woocommerce.API`) from env vars.
- `utils/api.py` — all WooCommerce REST calls (categories, attributes, terms, products), batched
  where the API supports it. Category/attribute/term sync here is always used (small volume, not a
  source of failures); `create_and_update_products`/`get_all_products` are the REST-batch product
  sync fallback (see "Sync products" above).
- `utils/wpcli_sync.py` — live product-sync path: builds the JSON payload (reusing the same
  `utils/utils.py`/`utils/func.py` helpers as the REST path), then pushes it over SSH/SFTP and runs
  it via `wp eval-file` (`paramiko`). No product-CRUD logic lives here — only payload shaping and
  SSH/SFTP orchestration; the actual WooCommerce writes are in `wpcli/sync_products.php`.
- `wpcli/sync_products.php` — deployed once to the WordPress server (not per run — see
  Configuration above). Does the create/update/outofstock work via WooCommerce's native CRUD.
- `utils/utils.py` — data shaping between DBF rows and WooCommerce payloads (grouping by product
  code, picking min/max price, computing total stock, building meta_data, the branch-name→slug map
  in `ru_to_lat`, Telegram notifier).
- `utils/func.py` — `generate_slug` (Cyrillic → Latin transliteration + slugify) and
  `remove_non_digits` (used to coerce SKUs back to numeric `codtmc` for comparison).

### Things to know before changing product-sync logic

- Product matching is entirely SKU-based, where SKU is the DBF `codtmc` field as a string — any
  logic dealing with "does this product already exist" goes through `existing_skus`/`existing_products`
  built from `sku`, not product name or ID.
- Attribute wiring is name-based: `get_attribute_id_by_name` looks up an attribute's WooCommerce ID
  by its Russian display name (e.g. `"Фармгруппа"`), so renaming an attribute on the WooCommerce
  side will silently break the corresponding sync unless `create_new_attributes`'s list in
  `utils/api.py` is updated to match.
- Branch/pharmacy names from DBF (`NAMEPODR`) are mapped to slugs through an explicit if/elif chain
  in `ru_to_lat` (`utils/utils.py`) — adding a new physical branch requires adding a case there, and
  the same three-branch allowlist inside `get_stocks_from_dbf` (`main.py`) controls which
  second-network branches get merged in at all.
