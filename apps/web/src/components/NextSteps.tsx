import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export type NextStepLink = {
  href: string;
  label: string;
  note: string;
};

export function NextSteps({ links }: { links: NextStepLink[] }) {
  return (
    <Card className="gap-3 py-5">
      <CardHeader className="px-5">
        <h2 className="text-xs font-medium tracking-wide text-gray-500 uppercase dark:text-gray-400">
          Keep going
        </h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 px-5 sm:flex-row sm:gap-8">
        {links.map((link) => {
          const external = link.href.startsWith("http");
          return (
            <Link
              key={link.href}
              href={link.href}
              target={external ? "_blank" : undefined}
              rel={external ? "noopener noreferrer" : undefined}
              className="flex-1"
            >
              <p className="text-sm font-medium text-accent underline underline-offset-2 hover:no-underline">
                {link.label} →
              </p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{link.note}</p>
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}
