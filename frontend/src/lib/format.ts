import type { Currency } from '@/types';

const DATE_FORMAT = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

const RELATIVE_FORMAT = new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' });

const MONEY_FORMAT: Record<Currency, Intl.NumberFormat> = {
  USD: new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }),
  INR: new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }),
};

export function formatDate(iso: string): string {
  return DATE_FORMAT.format(new Date(iso));
}

/** "3 days ago" / "in 2 weeks", relative to now. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const diffMs = new Date(iso).getTime() - now.getTime();
  const diffDays = Math.round(diffMs / 86_400_000);

  if (Math.abs(diffDays) < 1) return 'today';
  if (Math.abs(diffDays) < 7) return RELATIVE_FORMAT.format(diffDays, 'day');
  if (Math.abs(diffDays) < 30) return RELATIVE_FORMAT.format(Math.round(diffDays / 7), 'week');
  if (Math.abs(diffDays) < 365) return RELATIVE_FORMAT.format(Math.round(diffDays / 30), 'month');
  return RELATIVE_FORMAT.format(Math.round(diffDays / 365), 'year');
}

/** Locale-aware money, so ₹ and $ costs both render correctly. */
export function formatMoney(amount: number, currency: Currency = 'USD'): string {
  return MONEY_FORMAT[currency].format(amount);
}

/** Accepts a 0-1 ratio and renders it as a whole percentage. */
export function formatRatio(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

/** Accepts an already-scaled 0-100 score. */
export function formatScore(score: number): string {
  return String(Math.round(score));
}

export function formatDays(days: number): string {
  if (days === 0) return 'same day';
  if (days === 1) return '1 day';
  if (days < 14) return `${days} days`;
  return `${Math.round(days / 7)} weeks`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;

  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) return `${Math.round(kilobytes)} KB`;

  return `${(kilobytes / 1024).toFixed(1)} MB`;
}

export function clamp(value: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, value));
}

/** Time-of-day greeting for the dashboard header. */
export function greeting(now: Date = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return 'Good morning.';
  if (hour < 17) return 'Good afternoon.';
  return 'Good evening.';
}

/** "career" -> "Career", "business-model" -> "Business model". */
export function titleCase(value: string): string {
  const spaced = value.replace(/-/g, ' ');
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
