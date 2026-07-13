import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const WRAPPER_CLASSES = [
  "text-sm",
  "[&>*+*]:mt-3",
  "[&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-5",
  "[&_a]:underline [&_a]:underline-offset-2",
  "[&_code]:rounded [&_code]:bg-black/5 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs dark:[&_code]:bg-white/10",
  "[&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-black/5 [&_pre]:p-3 dark:[&_pre]:bg-white/10",
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0",
  "[&_blockquote]:border-l-2 [&_blockquote]:border-black/15 [&_blockquote]:pl-3 [&_blockquote]:italic dark:[&_blockquote]:border-white/15",
  "[&_table]:w-full [&_table]:border-collapse [&_th]:border-b [&_td]:border-t [&_th]:border-black/10 [&_td]:border-black/10 [&_th]:py-1 [&_td]:py-1 [&_th]:text-left dark:[&_th]:border-white/10 dark:[&_td]:border-white/10",
].join(" ");

export function Markdown({ content }: { content: string }) {
  return (
    <div className={WRAPPER_CLASSES}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
