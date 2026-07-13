import csv
import io
import math
import os
import sqlite3
from urllib.parse import urlencode

import markdown
from flask import Flask, abort, g, render_template, request, Response, jsonify

# Dynamic path to ensure it works locally and on Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "databasesapp.db")
METHODOLOGY_MD = os.path.join(BASE_DIR, "content", "methodology.md")
PER_PAGE = 25
MAX_PER_PAGE = 100

DOWNLOADS = {
    "loans": {
        "filename": "hudson_county_housing_2024.csv",
        "label": "Full loan-level dataset",
        "description": "Every 2024 HMDA mortgage application record for Hudson County, joined to its census tract's FFIEC income classification, NHPD subsidized-housing counts, and MOD-IV property data. One row per loan application.",
    },
    "nhpd_properties": {
        "filename": "hudson_county_nhpd_properties.csv",
        "label": "Subsidized housing owners (NHPD)",
        "description": "Every NHPD-tracked subsidized property in Hudson County, one row per property, with its real owner name, owner type, manager, unit count, and subsidy status.",
    },
    "parcel_ownership": {
        "filename": "hudson_county_parcel_ownership.csv",
        "label": "Apartment parcel ownership (MOD-IV)",
        "description": "Every Hudson County apartment parcel from NJ's MOD-IV tax assessment data, one row per parcel, with its mailing address, sale/deed history, and out-of-state owner flag.",
    },
}

PINNED_COLUMN = "census_tract"

COLUMN_GROUPS = [
    {
        "key": "flags",
        "label": "Investigation flags (computed)",
        "columns": [
            {"key": "ownership_profile", "label": "Ownership profile", "type": "text", "expr": """
                CASE
                    WHEN nhpd_property_count IS NULL OR nhpd_property_count = 0 THEN 'No subsidized housing'
                    WHEN nhpd_private_owned_properties > (COALESCE(nhpd_public_owned_properties,0) + COALESCE(nhpd_nonprofit_owned_properties,0))
                        THEN 'Majority privately owned'
                    WHEN nhpd_nonprofit_owned_properties >= nhpd_private_owned_properties
                         AND nhpd_nonprofit_owned_properties >= COALESCE(nhpd_public_owned_properties,0)
                        THEN 'Majority nonprofit-owned'
                    WHEN nhpd_public_owned_properties >= nhpd_private_owned_properties THEN 'Majority public-owned'
                    ELSE 'Mixed ownership'
                END
            """.strip()},
            {"key": "ownership_concentration", "label": "Avg. parcels per owner", "type": "num", "expr": """
                CASE WHEN modiv_distinct_owner_mailing_addresses IS NULL OR modiv_distinct_owner_mailing_addresses = 0
                     THEN NULL
                     ELSE ROUND(CAST(modiv_apt_parcel_count AS REAL) / modiv_distinct_owner_mailing_addresses, 2)
                END
            """.strip()},
        ],
    },
    {
        "key": "ownership",
        "label": "Property ownership & sales (MOD-IV)",
        "columns": [
            {"key": "nhpd_owners", "label": "Subsidized-property owner(s)", "type": "text", "expr": "nhpd_owners"},
            {"key": "nhpd_property_names", "label": "Subsidized property name(s)", "type": "text", "expr": "nhpd_property_names"},
            {"key": "modiv_distinct_owner_mailing_addresses", "label": "Distinct owner mailing addresses", "type": "num", "expr": "modiv_distinct_owner_mailing_addresses"},
            {"key": "modiv_out_of_area_owner_parcels", "label": "Out-of-area owner parcels", "type": "num", "expr": "modiv_out_of_area_owner_parcels"},
            {"key": "modiv_apt_parcel_count", "label": "Apartment parcels in tract", "type": "num", "expr": "modiv_apt_parcel_count"},
            {"key": "modiv_apt_total_units", "label": "Apartment units in tract", "type": "num", "expr": "modiv_apt_total_units"},
            {"key": "modiv_recent_sales_count", "label": "Recent sales count", "type": "num", "expr": "modiv_recent_sales_count"},
            {"key": "modiv_median_recent_sale_price", "label": "Median recent sale price", "type": "num", "expr": "modiv_median_recent_sale_price"},
            {"key": "modiv_most_recent_deed_date", "label": "Most recent deed date", "type": "text", "expr": "modiv_most_recent_deed_date"},
        ],
    },
    {
        "key": "subsidized",
        "label": "Subsidized housing (NHPD)",
        "columns": [
            {"key": "nhpd_property_count", "label": "Subsidized properties in tract", "type": "num", "expr": "nhpd_property_count"},
            {"key": "nhpd_total_units", "label": "Subsidized units in tract", "type": "num", "expr": "nhpd_total_units"},
            {"key": "nhpd_active_subsidies", "label": "Active subsidies", "type": "num", "expr": "nhpd_active_subsidies"},
            {"key": "nhpd_inactive_subsidies", "label": "Inactive/expired subsidies", "type": "num", "expr": "nhpd_inactive_subsidies"},
            {"key": "nhpd_private_owned_properties", "label": "Privately owned properties", "type": "num", "expr": "nhpd_private_owned_properties"},
            {"key": "nhpd_private_owned_units", "label": "Privately owned units", "type": "num", "expr": "nhpd_private_owned_units"},
            {"key": "nhpd_public_owned_properties", "label": "Publicly owned properties", "type": "num", "expr": "nhpd_public_owned_properties"},
            {"key": "nhpd_nonprofit_owned_properties", "label": "Nonprofit-owned properties", "type": "num", "expr": "nhpd_nonprofit_owned_properties"},
        ],
    },
    {
        "key": "tract",
        "label": "Tract income & demographics (FFIEC)",
        "columns": [
            {"key": "tract_income_level", "label": "Tract income level", "type": "text", "expr": "tract_income_level"},
            {"key": "tract_median_family_income", "label": "Tract median family income", "type": "num", "expr": "tract_median_family_income"},
            {"key": "tract_population", "label": "Tract population", "type": "num", "expr": "tract_population"},
            {"key": "tract_minority_pct", "label": "Tract minority %", "type": "num", "expr": "tract_minority_pct"},
        ],
    },
    {
        "key": "loan",
        "label": "Loan application (HMDA)",
        "columns": [
            {"key": "derived_race", "label": "Applicant race", "type": "text", "expr": "derived_race"},
            {"key": "derived_ethnicity", "label": "Applicant ethnicity", "type": "text", "expr": "derived_ethnicity"},
            {"key": "derived_sex", "label": "Applicant sex", "type": "text", "expr": "derived_sex"},
            {"key": "action", "label": "Loan outcome", "type": "text", "expr": "action"},
            {"key": "denial_reason_1", "label": "Denial reason", "type": "text", "expr": "denial_reason_1"},
            {"key": "denial_reason_2", "label": "Denial reason (2nd)", "type": "text", "expr": "denial_reason_2"},
            {"key": "applicant_income_000s", "label": "Applicant income ($000s)", "type": "num", "expr": "applicant_income_000s"},
        ],
    },
]

ALL_COLUMNS = {PINNED_COLUMN: {"key": PINNED_COLUMN, "label": "Census tract", "type": "text", "expr": "census_tract"}}
for group in COLUMN_GROUPS:
    for col in group["columns"]:
        ALL_COLUMNS[col["key"]] = col

DEFAULT_COLUMNS = [
    "ownership_profile",
    "ownership_concentration",
    "nhpd_private_owned_properties",
    "nhpd_public_owned_properties",
    "nhpd_nonprofit_owned_properties",
    "nhpd_owners",
    "nhpd_property_names",
    "modiv_distinct_owner_mailing_addresses",
    "modiv_out_of_area_owner_parcels",
    "modiv_median_recent_sale_price",
    "modiv_most_recent_deed_date",
    "tract_income_level",
]

FILTERABLE_COLUMNS = {
    "ownership_profile": ALL_COLUMNS["ownership_profile"]["expr"],
    "tract_income_level": "tract_income_level",
    "derived_race": "derived_race",
    "derived_ethnicity": "derived_ethnicity",
    "derived_sex": "derived_sex",
    "action": "action",
    "denial_reason_1": "denial_reason_1",
}

RANGE_FILTERS = {
    "income": "applicant_income_000s",
    "minority": "tract_minority_pct",
    "nhpd_units": "nhpd_total_units",
    "out_of_area": "modiv_out_of_area_owner_parcels",
    "concentration": ALL_COLUMNS["ownership_concentration"]["expr"],
}

DEFAULT_SORT = "ownership_concentration"

OWNERSHIP_PER_PAGE = 20

NHPD_COLUMNS = [
    ("property_name", "Property name", "text"),
    ("property_address", "Address", "text"),
    ("census_tract", "Census tract", "text"),
    ("total_units", "Units", "num"),
    ("owner", "Owner", "text"),
    ("owner_type", "Owner type", "text"),
    ("manager_name", "Manager", "text"),
    ("manager_type", "Manager type", "text"),
    ("property_status", "Status", "text"),
    ("active_subsidies", "Active subsidies", "num"),
]
NHPD_SORTABLE = {c[0] for c in NHPD_COLUMNS}
NHPD_DEFAULT_SORT = "total_units"

ADDR_COLUMNS = [
    ("owner_mailing_key", "Owner mailing address", "text"),
    ("parcel_count", "Parcels", "num"),
    ("total_units", "Units", "num"),
    ("tract_count", "Distinct tracts", "num"),
    ("out_of_state_count", "Out-of-state parcels", "num"),
    ("cities", "Municipalities", "text"),
]
ADDR_SORTABLE = {"owner_mailing_key", "parcel_count", "total_units", "tract_count", "out_of_state_count"}
ADDR_DEFAULT_SORT = "parcel_count"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db


def close_db(exception=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def resolve_columns(args):
    requested = [c for c in args.getlist("cols") if c in ALL_COLUMNS]
    cols = requested if requested else list(DEFAULT_COLUMNS)
    if PINNED_COLUMN in cols:
        cols.remove(PINNED_COLUMN)
    return [PINNED_COLUMN] + cols


def resolve_sort(args):
    sort_key = args.get("sort", DEFAULT_SORT)
    if sort_key not in ALL_COLUMNS:
        sort_key = DEFAULT_SORT
    direction = "ASC" if args.get("dir") == "asc" else "DESC"
    return sort_key, direction


def build_filters(args):
    clauses = []
    params = []

    q = (args.get("q") or "").strip()
    if q:
        clauses.append("(census_tract LIKE ? OR nhpd_property_names LIKE ? OR nhpd_owners LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    for col, expr in FILTERABLE_COLUMNS.items():
        val = args.get(col)
        if val:
            clauses.append(f"({expr}) = ?")
            params.append(val)

    for prefix, expr in RANGE_FILTERS.items():
        min_val = args.get(f"{prefix}_min")
        if min_val:
            clauses.append(f"({expr}) >= ?")
            params.append(float(min_val))
        max_val = args.get(f"{prefix}_max")
        if max_val:
            clauses.append(f"({expr}) <= ?")
            params.append(float(max_val))

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def get_filter_options(db):
    options = {}
    for col, expr in FILTERABLE_COLUMNS.items():
        rows = db.execute(
            f"SELECT DISTINCT ({expr}) AS v FROM loans WHERE ({expr}) IS NOT NULL AND ({expr}) != '' ORDER BY v"
        ).fetchall()
        options[col] = [r[0] for r in rows]
    return options


def create_app():
    app = Flask(__name__)
    app.teardown_appcontext(close_db)

    @app.template_global()
    def merge_args(**overrides):
        merged_pairs = [(k, v) for k, v in request.args.items(multi=True)]
        for key, value in overrides.items():
            merged_pairs = [(k, v) for k, v in merged_pairs if k != key]
            if value is not None:
                merged_pairs.append((key, value))
        return urlencode(merged_pairs)

    @app.template_global()
    def sort_link(col_key, col_type):
        active_sort = request.args.get("sort", DEFAULT_SORT)
        if col_key == active_sort:
            current_dir = "asc" if request.args.get("dir") == "asc" else "desc"
            next_dir = "desc" if current_dir == "asc" else "asc"
        else:
            next_dir = "asc" if col_type == "text" else "desc"
        return "?" + merge_args(sort=col_key, dir=next_dir, page=None)

    @app.template_global()
    def sort_indicator(col_key):
        active_sort = request.args.get("sort", DEFAULT_SORT)
        if col_key != active_sort:
            return ""
        current_dir = "asc" if request.args.get("dir") == "asc" else "desc"
        return " ▲" if current_dir == "asc" else " ▼"

    @app.template_global()
    def sort_link_for(prefix, col_key, col_type, default_sort):
        sort_param, dir_param, page_param = f"{prefix}sort", f"{prefix}dir", f"{prefix}page"
        active_sort = request.args.get(sort_param, default_sort)
        if col_key == active_sort:
            current_dir = "asc" if request.args.get(dir_param) == "asc" else "desc"
            next_dir = "desc" if current_dir == "asc" else "asc"
        else:
            next_dir = "asc" if col_type == "text" else "desc"
        return "?" + merge_args(**{sort_param: col_key, dir_param: next_dir, page_param: None})

    @app.template_global()
    def sort_indicator_for(prefix, col_key, default_sort):
        sort_param, dir_param = f"{prefix}sort", f"{prefix}dir"
        active_sort = request.args.get(sort_param, default_sort)
        if col_key != active_sort:
            return ""
        current_dir = "asc" if request.args.get(dir_param) == "asc" else "desc"
        return " ▲" if current_dir == "asc" else " ▼"

    @app.route("/")
    def index():
        db = get_db()
        where, params = build_filters(request.args)
        cols = resolve_columns(request.args)
        sort_key, direction = resolve_sort(request.args)

        total = db.execute(f"SELECT COUNT(*) FROM loans {where}", params).fetchone()[0]

        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            page = 1
        try:
            per_page = min(MAX_PER_PAGE, max(1, int(request.args.get("per_page", PER_PAGE))))
        except ValueError:
            per_page = PER_PAGE

        total_pages = max(1, math.ceil(total / per_page))
        page = min(page, total_pages)
        offset = (page - 1) * per_page

        select_sql = ", ".join(f"({ALL_COLUMNS[c]['expr']}) AS {c}" for c in cols)
        sort_expr = ALL_COLUMNS[sort_key]["expr"]
        rows = db.execute(
            f"""SELECT {select_sql} FROM loans {where}
                ORDER BY ({sort_expr}) {direction}, rowid
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        dataset_total = db.execute("SELECT COUNT(*) FROM loans").fetchone()[0]

        return render_template(
            "index.html",
            rows=rows,
            columns=[ALL_COLUMNS[c] for c in cols],
            column_groups=COLUMN_GROUPS,
            selected_cols=set(cols),
            pinned_column=PINNED_COLUMN,
            sort_key=sort_key,
            sort_dir=direction,
            total=total,
            dataset_total=dataset_total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            args=request.args,
            options=get_filter_options(db),
        )

    @app.route("/export.csv")
    def export_csv():
        db = get_db()
        where, params = build_filters(request.args)
        scope = request.args.get("scope", "visible")
        cols = resolve_columns(request.args) if scope == "visible" else list(ALL_COLUMNS.keys())
        sort_key, direction = resolve_sort(request.args)

        select_sql = ", ".join(f"({ALL_COLUMNS[c]['expr']}) AS {c}" for c in cols)
        sort_expr = ALL_COLUMNS[sort_key]["expr"]
        rows = db.execute(
            f"""SELECT {select_sql} FROM loans {where} ORDER BY ({sort_expr}) {direction}, rowid""",
            params,
        ).fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([ALL_COLUMNS[c]["label"] for c in cols])
        for row in rows:
            writer.writerow(list(row))

        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=hudson_housing_ownership.csv"},
        )

    @app.route("/api/count")
    def api_count():
        db = get_db()
        where, params = build_filters(request.args)
        total = db.execute(f"SELECT COUNT(*) FROM loans {where}", params).fetchone()[0]
        dataset_total = db.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
        return jsonify({"count": total, "dataset_total": dataset_total})

    @app.route("/methodology")
    def methodology():
        db = get_db()
        dataset_total = db.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
        column_metadata = db.execute(
            "SELECT column_name, granularity, note FROM column_metadata"
        ).fetchall()
        with open(METHODOLOGY_MD, encoding="utf-8") as f:
            methodology_html = markdown.markdown(f.read())
        return render_template(
            "methodology.html",
            options=get_filter_options(db),
            dataset_total=dataset_total,
            column_metadata=column_metadata,
            methodology_html=methodology_html,
        )

    @app.route("/download")
    def download_page():
        db = get_db()
        datasets = []
        for key, meta in DOWNLOADS.items():
            count = db.execute(f"SELECT COUNT(*) FROM {key}").fetchone()[0]
            datasets.append({**meta, "key": key, "count": count})
        column_metadata = db.execute(
            "SELECT column_name, granularity, note FROM column_metadata"
        ).fetchall()
        return render_template("download.html", datasets=datasets, column_metadata=column_metadata)

    @app.route("/download/<dataset_key>.csv")
    def download_csv(dataset_key):
        if dataset_key not in DOWNLOADS:
            abort(404)
        db = get_db()
        columns = [r[1] for r in db.execute(f"PRAGMA table_info({dataset_key})").fetchall()]
        rows = db.execute(f"SELECT * FROM {dataset_key} ORDER BY rowid").fetchall()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(list(row))

        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={DOWNLOADS[dataset_key]['filename']}"},
        )

    @app.route("/ownership")
    def ownership():
        db = get_db()

        n_clauses, n_params = [], []
        nq = (request.args.get("nq") or "").strip()
        if nq:
            n_clauses.append(
                "(owner LIKE ? OR manager_name LIKE ? OR property_name LIKE ? OR property_address LIKE ?)"
            )
            like = f"%{nq}%"
            n_params.extend([like, like, like, like])
        if request.args.get("owner_type"):
            n_clauses.append("owner_type = ?")
            n_params.append(request.args["owner_type"])
        if request.args.get("property_status"):
            n_clauses.append("property_status = ?")
            n_params.append(request.args["property_status"])
        n_where = f"WHERE {' AND '.join(n_clauses)}" if n_clauses else ""

        n_sort = request.args.get("nsort", NHPD_DEFAULT_SORT)
        if n_sort not in NHPD_SORTABLE:
            n_sort = NHPD_DEFAULT_SORT
        n_dir = "ASC" if request.args.get("ndir") == "asc" else "DESC"

        n_total = db.execute(f"SELECT COUNT(*) FROM nhpd_properties {n_where}", n_params).fetchone()[0]
        try:
            n_page = max(1, int(request.args.get("npage", 1)))
        except ValueError:
            n_page = 1
        n_total_pages = max(1, math.ceil(n_total / OWNERSHIP_PER_PAGE))
        n_page = min(n_page, n_total_pages)

        nhpd_rows = db.execute(
            f"""SELECT {', '.join(c[0] for c in NHPD_COLUMNS)} FROM nhpd_properties {n_where}
                ORDER BY {n_sort} {n_dir}
                LIMIT ? OFFSET ?""",
            n_params + [OWNERSHIP_PER_PAGE, (n_page - 1) * OWNERSHIP_PER_PAGE],
        ).fetchall()

        owner_types = [r[0] for r in db.execute(
            "SELECT DISTINCT owner_type FROM nhpd_properties WHERE owner_type IS NOT NULL AND owner_type != '' ORDER BY owner_type"
        ).fetchall()]
        property_statuses = [r[0] for r in db.execute(
            "SELECT DISTINCT property_status FROM nhpd_properties WHERE property_status IS NOT NULL AND property_status != '' ORDER BY property_status"
        ).fetchall()]

        a_clauses, a_params = ["owner_mailing_key IS NOT NULL", "owner_mailing_key != ''"], []
        aq = (request.args.get("aq") or "").strip()
        if aq:
            a_clauses.append("owner_mailing_key LIKE ?")
            a_params.append(f"%{aq}%")
        a_where = f"WHERE {' AND '.join(a_clauses)}"

        having_clauses, having_params = [], []
        min_parcels = request.args.get("min_parcels")
        if min_parcels:
            having_clauses.append("parcel_count >= ?")
            having_params.append(int(min_parcels))
        a_having = f"HAVING {' AND '.join(having_clauses)}" if having_clauses else ""

        a_sort = request.args.get("asort", ADDR_DEFAULT_SORT)
        if a_sort not in ADDR_SORTABLE:
            a_sort = ADDR_DEFAULT_SORT
        a_dir = "ASC" if request.args.get("adir") == "asc" else "DESC"

        group_sql = f"""
            SELECT owner_mailing_key,
                   COUNT(*) AS parcel_count,
                   SUM(dwell) AS total_units,
                   COUNT(DISTINCT census_tract) AS tract_count,
                   SUM(CASE WHEN out_of_state_owner = 'True' THEN 1 ELSE 0 END) AS out_of_state_count,
                   GROUP_CONCAT(DISTINCT mun_name) AS cities
            FROM parcel_ownership
            {a_where}
            GROUP BY owner_mailing_key
            {a_having}
        """
        a_total = db.execute(f"SELECT COUNT(*) FROM ({group_sql})", a_params + having_params).fetchone()[0]
        try:
            a_page = max(1, int(request.args.get("apage", 1)))
        except ValueError:
            a_page = 1
        a_total_pages = max(1, math.ceil(a_total / OWNERSHIP_PER_PAGE))
        a_page = min(a_page, a_total_pages)

        addr_rows = db.execute(
            f"""SELECT * FROM ({group_sql}) ORDER BY {a_sort} {a_dir} LIMIT ? OFFSET ?""",
            a_params + having_params + [OWNERSHIP_PER_PAGE, (a_page - 1) * OWNERSHIP_PER_PAGE],
        ).fetchall()

        return render_template(
            "ownership.html",
            nhpd_rows=nhpd_rows,
            nhpd_columns=NHPD_COLUMNS,
            nhpd_default_sort=NHPD_DEFAULT_SORT,
            n_total=n_total,
            n_page=n_page,
            n_total_pages=n_total_pages,
            owner_types=owner_types,
            property_statuses=property_statuses,
            addr_rows=addr_rows,
            addr_columns=ADDR_COLUMNS,
            addr_default_sort=ADDR_DEFAULT_SORT,
            a_total=a_total,
            a_page=a_page,
            a_total_pages=a_total_pages,
            args=request.args,
        )

    @app.route("/ownership/address/<path:mailing_key>")
    def ownership_address_detail(mailing_key):
        db = get_db()
        parcels = db.execute(
            """SELECT prop_loc, mun_name, census_tract, dwell, sale_price, deed_date,
                      out_of_state_owner, land_val, net_value
               FROM parcel_ownership WHERE owner_mailing_key = ? ORDER BY prop_loc""",
            [mailing_key],
        ).fetchall()
        return render_template("ownership_address.html", mailing_key=mailing_key, parcels=parcels)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
