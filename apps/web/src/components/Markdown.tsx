import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const WRAPPER_CLASSES = [
  "text-base leading-relaxed",
  "[&>*+*]:mt-4",
  "[&_h1]:mt-10 [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:first:mt-0",
  "[&_h2]:mt-9 [&_h2]:border-t [&_h2]:border-black/10 [&_h2]:pt-6 [&_h2]:text-lg [&_h2]:font-semibold dark:[&_h2]:border-white/10",
  "[&_h3]:mt-5 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:uppercase [&_h3]:tracking-wide [&_h3]:text-gray-500 dark:[&_h3]:text-gray-400",
  "[&_p]:max-w-prose [&_p]:leading-relaxed",
  "[&_ul]:max-w-prose [&_ol]:max-w-prose [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-5 [&_li+li]:mt-1",
  "[&_a]:underline [&_a]:underline-offset-2",
  "[&_hr]:my-6 [&_hr]:border-black/10 dark:[&_hr]:border-white/10",
  "[&_code]:rounded [&_code]:bg-black/5 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs dark:[&_code]:bg-white/10",
  "[&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-black/5 [&_pre]:p-3 dark:[&_pre]:bg-white/10",
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0",
  "[&_blockquote]:border-l-2 [&_blockquote]:border-black/15 [&_blockquote]:pl-3 [&_blockquote]:italic dark:[&_blockquote]:border-white/15",
  "[&_table]:w-full [&_table]:border-collapse [&_th]:border-b [&_td]:border-t [&_th]:border-black/10 [&_td]:border-black/10 [&_th]:py-1.5 [&_td]:py-1.5 [&_th]:text-left dark:[&_th]:border-white/10 dark:[&_td]:border-white/10",
].join(" ");

export function Markdown({ content }: { content: string }) {
  return (
    <div className={WRAPPER_CLASSES}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
