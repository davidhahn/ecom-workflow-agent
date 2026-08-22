import type { ToolCallEntry } from "@/lib/api";
import { JsonPreview } from "@/components/JsonPreview";

export function ToolCallTrace({
  toolCalls,
  totalLatencyMs,
  llmLatencyMs,
}: {
  toolCalls: ToolCallEntry[];
  totalLatencyMs: number;
  // Measured LLM call time (RequestLog.llm_latency_ms). Omit or pass null
  // for a row logged before that column existed; the summary line falls
  // back to the old split when it's missing.
  llmLatencyMs?: number | null;
}) {
  if (toolCalls.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-gray-400">
        No tool calls made for this request.
      </p>
    );
  }

  const sumLatencyMs = toolCalls.reduce((sum, call) => sum + call.latency_ms, 0);

  return (
    <div className="flex flex-col gap-3">
      {llmLatencyMs != null ? (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Total request time: <span className="font-medium text-foreground">{totalLatencyMs} ms</span>
          {" · "}Claude API calls:{" "}
          <span className="font-medium text-foreground">{llmLatencyMs} ms</span>
          {" · "}Tool execution:{" "}
          <span className="font-medium text-foreground">{sumLatencyMs} ms</span>
          {" · "}Other (network, logging):{" "}
          <span className="font-medium text-foreground">
            {Math.max(0, totalLatencyMs - llmLatencyMs - sumLatencyMs)} ms
          </span>
        </p>
      ) : (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Total request latency: <span className="font-medium text-foreground">{totalLatencyMs} ms</span>
          {" · "}Sum of tool-call latencies:{" "}
          <span className="font-medium text-foreground">{sumLatencyMs} ms</span>
          {" · "}Remaining (LLM thinking / orchestration):{" "}
          <span className="font-medium text-foreground">{totalLatencyMs - sumLatencyMs} ms</span>
        </p>
      )}
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-black/10 text-gray-500 dark:border-white/10 dark:text-gray-400">
            <th className="py-1 pr-3 font-medium">#</th>
            <th className="py-1 pr-3 font-medium">Tool</th>
            <th className="py-1 pr-3 font-medium">Latency</th>
            <th className="py-1 pr-3 font-medium">Input</th>
            <th className="py-1 pr-3 font-medium">Output</th>
          </tr>
        </thead>
        <tbody>
          {toolCalls.map((call) => (
            <tr key={call.sequence} className="border-b border-black/5 align-top dark:border-white/5">
              <td className="py-1.5 pr-3">{call.sequence}</td>
              <td className="py-1.5 pr-3 whitespace-nowrap font-mono">{call.tool_name}</td>
              <td className="py-1.5 pr-3 whitespace-nowrap">{call.latency_ms} ms</td>
              <td className="py-1.5 pr-3">
                <JsonPreview value={call.input} />
              </td>
              <td className="py-1.5 pr-3">
                <JsonPreview value={call.output} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
