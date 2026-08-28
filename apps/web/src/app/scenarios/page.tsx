import { ScenarioDemo } from "@/components/ScenarioDemo";

export const metadata = {
  title: "Scenarios",
};

export default function ScenariosPage() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold">Scenarios</h1>
        <p className="max-w-prose text-base text-gray-600 dark:text-gray-300">
          Run a curated case and compare the result against the behavior promised up front.
        </p>
      </div>

      <ScenarioDemo />
    </div>
  );
}
