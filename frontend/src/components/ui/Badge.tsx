import type { ComponentPropsWithRef } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import { toneFill, toneSurface, toneText } from '@/lib/tone';
import type { Tone } from '@/types';

export type BadgeVariant = 'soft' | 'outline';

export interface BadgeProps extends ComponentPropsWithRef<'span'> {
  tone?: Tone;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  /** Small status dot, tinted to match the tone. */
  dot?: boolean;
  icon?: LucideIcon;
}

export function Badge({
  tone = 'neutral',
  variant = 'soft',
  size = 'md',
  dot = false,
  icon: Icon,
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-sm border font-medium',
        size === 'sm' ? 'px-1.5 py-0.5 text-micro' : 'px-2 py-0.5 text-small',
        variant === 'soft' ? toneSurface[tone] : cn('border-hairline bg-transparent', toneText[tone]),
        className,
      )}
      {...rest}
    >
      {dot ? <span className={cn('size-1.5 rounded-full', toneFill[tone])} aria-hidden /> : null}
      {Icon ? <Icon className="size-3.5" aria-hidden /> : null}
      {children}
    </span>
  );
}
