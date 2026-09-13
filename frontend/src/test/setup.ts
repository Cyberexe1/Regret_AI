import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom has no IntersectionObserver/ResizeObserver implementation, but
// framer-motion's viewport-triggered animations (used by <Reveal>, etc.)
// probe for one on mount. A minimal no-op stub is enough for tests that
// only assert on rendered content, never on animation behavior itself.
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

class MockResizeObserver implements ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

// jsdom has no scrollIntoView implementation either - used by the intake
// progress rail and "Try an example" to scroll to a section. A no-op is
// enough for tests that only assert on rendered content/state.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

afterEach(() => {
  cleanup();
});
