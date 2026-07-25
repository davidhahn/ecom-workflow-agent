ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
    "refunds",
    "support_tickets",
    "web_analytics",
    "campaigns",
}

# Column-level exclusion: never show this to the model, never allow it in a
# SELECT list, and never grant SELECT on it to the DB role that runs these
# queries (layer 3 backstop for layers 1-2).
BLOCKED_COLUMNS = {("customers", "email")}

BLOCKED_FUNCTIONS = {
    "pg_sleep",
    "pg_sleep_for",
    "pg_sleep_until",
    "dblink",
    "dblink_connect",
    "dblink_exec",
    "lo_import",
    "lo_export",
    "lo_read",
    "lo_write",
    "copy",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_ls_logdir",
    "pg_ls_waldir",
    "pg_stat_file",
    "pg_terminate_backend",
    "pg_cancel_backend",
}
