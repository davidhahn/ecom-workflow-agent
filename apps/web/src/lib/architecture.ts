// The Architecture page renders this full table. The home page cites just
// the row count as a proof stat, so the two numbers can't fall out of sync.
export const RESPONSIBILITY_ROWS: { llm: string; enforced: string }[] = [
  { llm: "tool selection", enforced: "tool permissions (`require_permission` checks the calling role before any tool runs)" },
  {
    llm: "candidate SQL",
    enforced:
      "SQL AST allowlist (`validate_ast` checks tables, columns, and functions against an allowlist, and blocks bare `SELECT *`)",
  },
  {
    llm: "request field extraction (refund reason, ticket category, pulled from free text)",
    enforced: "query-cost limit (`check_cost` rejects a query whose `EXPLAIN` cost crosses a threshold, before it runs)",
  },
  {
    llm: "policy interpretation (reading retrieved RAG chunks)",
    enforced:
      "DB privilege boundary (the `ops_agent_readonly` role restricts columns and caps every query at a 5-second timeout, even if the checks above it fail)",
  },
  {
    llm: "synthesis (turning SQL rows or RAG chunks into an answer)",
    enforced:
      "refund waterfall (`evaluate_refund` runs a fixed rule sequence: return window, final-sale exemption, repeat-refund flag, $200 approval threshold)",
  },
  {
    llm: "explanation (why the answer says what it says)",
    enforced:
      "draft/confirm ticket lifecycle (`draft_support_ticket` creates a draft in memory, and a second call, `confirm_support_ticket`, under its own permission, writes it to the database)",
  },
  {
    llm: "",
    enforced: "groundedness check (`check_groundedness` matches cited rule numbers and titles against the chunks retrieved for that answer)",
  },
];
