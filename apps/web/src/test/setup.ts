import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest doesn't expose afterEach globally by default (test.globals isn't
// set), so @testing-library/react's own auto-cleanup — which relies on
// detecting a global afterEach — never runs on its own. Without this, a
// render() in one test stays mounted into the next test in the same file,
// so e.g. a second render() makes getByRole match two of the same button.
afterEach(() => {
  cleanup();
});
