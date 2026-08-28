import { GITHUB_REPO_URL } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-black/10 px-6 py-8 text-xs text-gray-500 dark:border-white/10 dark:text-gray-400">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
        <span>Built by David Hahn.</span>
        <div className="flex flex-wrap items-center gap-4">
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent"
          >
            GitHub
          </a>
          <a
            href="https://blog.davidhahn.co/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent"
          >
            Blog
          </a>
          <span className="font-mono text-gray-400 dark:text-gray-600">
            Next.js · FastAPI · Claude
          </span>
        </div>
      </div>
    </footer>
  );
}
