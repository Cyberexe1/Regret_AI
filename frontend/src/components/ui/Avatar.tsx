import { cn } from '@/lib/cn';
import type { Size } from '@/types';

const SIZE: Record<Size, string> = {
  sm: 'size-7 text-micro',
  md: 'size-9 text-small',
  lg: 'size-11 text-body',
};

function initialsFrom(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

export interface AvatarProps {
  name: string;
  /** Optional user-supplied image; falls back to initials when absent. */
  src?: string;
  size?: Size;
  className?: string;
}

export function Avatar({ name, src, size = 'md', className }: AvatarProps) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-hairline-strong bg-accent-soft font-medium text-accent-ink select-none',
        SIZE[size],
        className,
      )}
      title={name}
    >
      {src ? (
        <img src={src} alt={name} className="size-full object-cover" />
      ) : (
        <span aria-hidden>{initialsFrom(name)}</span>
      )}
      {src ? null : <span className="sr-only">{name}</span>}
    </span>
  );
}
