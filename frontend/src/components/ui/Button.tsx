import type { ComponentPropsWithRef, ReactNode } from 'react';
import { Loader2, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { Size } from '@/types';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'link';

const BASE =
  'inline-flex items-center justify-center gap-2 rounded-md font-medium whitespace-nowrap ' +
  'transition-[background-color,border-color,color,opacity] duration-150 ease-out ' +
  'disabled:pointer-events-none disabled:opacity-45';

const VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-white shadow-soft hover:bg-accent-hover active:bg-accent-press',
  secondary:
    'border border-hairline bg-surface-raised text-ink hover:border-hairline-strong hover:bg-surface-overlay',
  ghost: 'text-ink-secondary hover:bg-surface-raised hover:text-ink',
  danger:
    'border border-danger-line bg-danger-soft text-danger-ink hover:border-danger hover:bg-danger/20',
  link: 'text-accent-ink underline-offset-4 hover:text-ink hover:underline',
};

const SIZE: Record<Size, string> = {
  sm: 'h-8 px-3 text-small',
  md: 'h-9.5 px-4 text-small',
  lg: 'h-11 px-5 text-body',
};

const ICON_ONLY_SIZE: Record<Size, string> = {
  sm: 'size-8 p-0',
  md: 'size-9.5 p-0',
  lg: 'size-11 p-0',
};

const ICON_SIZE: Record<Size, string> = {
  sm: 'size-3.5',
  md: 'size-4',
  lg: 'size-4.5',
};

/**
 * Exposed so anchor-like elements (react-router `Link`) can adopt button
 * styling without duplicating the variant table.
 */
export function buttonClasses(options: {
  variant?: ButtonVariant;
  size?: Size;
  iconOnly?: boolean;
  fullWidth?: boolean;
  className?: string;
} = {}): string {
  const { variant = 'primary', size = 'md', iconOnly = false, fullWidth = false, className } = options;

  return cn(
    BASE,
    VARIANT[variant],
    iconOnly ? ICON_ONLY_SIZE[size] : SIZE[size],
    variant === 'link' && 'h-auto px-0',
    fullWidth && 'w-full',
    className,
  );
}

export interface ButtonProps extends Omit<ComponentPropsWithRef<'button'>, 'children'> {
  variant?: ButtonVariant;
  size?: Size;
  /** Renders a square button; pass an aria-label when using this. */
  iconOnly?: boolean;
  fullWidth?: boolean;
  loading?: boolean;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
  children?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  iconOnly = false,
  fullWidth = false,
  loading = false,
  leftIcon: LeftIcon,
  rightIcon: RightIcon,
  className,
  disabled,
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  const iconClass = ICON_SIZE[size];

  return (
    <button
      type={type}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      className={buttonClasses({ variant, size, iconOnly, fullWidth, className })}
      {...rest}
    >
      {loading ? (
        <Loader2 className={cn(iconClass, 'animate-spin')} aria-hidden />
      ) : (
        LeftIcon && <LeftIcon className={iconClass} aria-hidden />
      )}
      {!iconOnly && children}
      {!loading && RightIcon && <RightIcon className={iconClass} aria-hidden />}
    </button>
  );
}
