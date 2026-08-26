// TODO: replace with the real repo URL before deploying.
const GITHUB_REPO_URL = "https://github.com/davidhahn/ecom-workflow-agent";

// No case-study URL provided yet. Per instructions, the "Read the case
// study" link is omitted entirely (not rendered pointing at a placeholder)
// until a real URL exists. Set this to bring the link back.
const CASE_STUDY_URL: string | null = null;

export function IntroBanner() {
  return (
    <div className="border-b border-black/10 bg-black/[0.03] px-4 py-2 text-xs text-gray-600 dark:border-white/10 dark:bg-white/[0.03] dark:text-gray-400">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          A demo AI ops agent for an eCommerce business. Ask a question or evaluate a refund, then
          see the full decision trace behind it.
        </span>
        <a
          href={GITHUB_REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium underline underline-offset-2 hover:no-underline"
        >
          View on GitHub
        </a>
        {CASE_STUDY_URL && (
          <a
            href={CASE_STUDY_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline underline-offset-2 hover:no-underline"
          >
            Read the case study
          </a>
        )}
      </div>
    </div>
  );
}
