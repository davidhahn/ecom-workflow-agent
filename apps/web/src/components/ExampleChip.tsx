// type="button" is load-bearing: these render inside a <form>, and a
// <button> without an explicit type defaults to type="submit", which
// would auto-submit the form on click. Examples only populate a field;
// the user still has to press the real submit button themselves.
export function ExampleChip({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-black/15 px-3 py-1.5 text-left text-xs text-gray-600 hover:border-black/30 hover:bg-black/5 dark:border-white/15 dark:text-gray-300 dark:hover:border-white/30 dark:hover:bg-white/5"
    >
      {label}
    </button>
  );
}
