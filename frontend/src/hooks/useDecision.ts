import { useMemo } from 'react';
import { findDecision } from '@/data/decisions';
import type { Decision } from '@/types';

/**
 * Resolves a decision by id or alias. Goes through `findDecision` so alias
 * handling (for example `/decision/demo`) lives in one place.
 */
export function useDecision(id: string | undefined): Decision | undefined {
  return useMemo(() => (id ? findDecision(id) : undefined), [id]);
}
