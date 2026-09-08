import type { ComponentPropsWithRef, ElementType, ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type CardVariant = 'default' | 'raised' | 'inset' | 'quiet';
export type CardPadding = 'none' | 'sm' | 'md' | 'lg';

const VARIANT: Record<CardVariant, string> = {
  default: 'border border-hairline bg-surface shadow-soft',
  raised: 'border border-hairline-strong bg-surface-raised shadow-raised',
  inset: 'border border-hairline bg-surface-inset',
  quiet: 'border border-hairline/60 bg-transparent',
};

const PADDING: Record<CardPadding, string> = {
  none: '',
  sm: 'p-3.5',
  md: 'p-5',
  lg: 'p-6 md:p-7',
};

export interface CardProps extends ComponentPropsWithRef<'div'> {
  variant?: CardVariant;
  padding?: CardPadding;
  /** Adds hover affordance for cards that navigate somewhere. */
  interactive?: boolean;
  as?: ElementType;
}

export function Card({
  variant = 'default',
  padding = 'md',
  interactive = false,
  as: Tag = 'div',
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cn(
        'rounded-xl',
        VARIANT[variant],
        PADDING[padding],
        interactive &&
          'cursor-pointer transition-colors duration-150 hover:border-hairline-strong hover:bg-surface-raised',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export interface CardHeaderProps extends ComponentPropsWithRef<'div'> {
  /** Right-aligned slot for badges, menus or filters. */
  action?: ReactNode;
}

export function CardHeader({ action, className, children, ...rest }: CardHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4', className)} {...rest}>
      <div className="min-w-0 space-y-1">{children}</div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function CardTitle({ className, children, ...rest }: ComponentPropsWithRef<'h3'>) {
  return (
    <h3 className={cn('text-card-title text-ink', className)} {...rest}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, children, ...rest }: ComponentPropsWithRef<'p'>) {
  return (
    <p className={cn('text-small text-ink-secondary', className)} {...rest}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...rest }: ComponentPropsWithRef<'div'>) {
  return (
    <div className={cn('text-body text-ink-secondary', className)} {...rest}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...rest }: ComponentPropsWithRef<'div'>) {
  return (
    <div
      className={cn('flex flex-wrap items-center gap-3 border-t border-hairline pt-4', className)}
      {...rest}
    >
      {children}
    </div>
  );
}
