"use client";

import { useState } from "react";

const TRUNCATE_AT = 80;

// Click-to-expand raw JSON, used for tool-call input/output in the activity
// trace view — those payloads range from a one-line query object to a full
// RAG chunk list, too wide to always show inline in a table cell.
export function JsonPreview({ value }: { value: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const oneLine = JSON.stringify(value) ?? "null";

  if (oneLine.length <= TRUNCATE_AT) {
    return <code className="text-xs whitespace-pre-wrap break-all">{oneLine}</code>;
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="text-left text-xs text-gray-500 underline decoration-dotted hover:text-foreground dark:text-gray-400"
      >
        {expanded ? "Collapse" : `${oneLine.slice(0, TRUNCATE_AT)}…`}
      </button>
      {expanded && (
        <pre className="mt-1 max-w-xl overflow-x-auto rounded-md bg-black/5 p-2 text-xs dark:bg-white/5">
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  );
}
