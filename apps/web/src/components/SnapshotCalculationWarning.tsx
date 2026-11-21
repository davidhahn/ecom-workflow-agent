import Link from "next/link";

export function SnapshotCalculationWarning() {
  return (
    <aside className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
      <p className="font-medium">Saved example: a calculation failure</p>
      <p className="mt-2 max-w-prose">
        This older run counted order lines instead of units and included refunds that weren’t
        approved. That put Final Sale first when it should have been Electronics. I’ve kept the
        original result below so the failure is visible. The live path now uses unit quantities
        and approved refunds; run it fresh to inspect the current answer and SQL.
      </p>
      <Link
        href="/evaluation-lab#findings-finding-2-sql-calculation-errors"
        className="mt-2 inline-block font-medium underline underline-offset-2 hover:no-underline"
      >
        Read the calculation investigation →
      </Link>
    </aside>
  );
}
