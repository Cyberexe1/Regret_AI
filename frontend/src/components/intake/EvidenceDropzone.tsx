import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
  File as FileIcon,
  FileImage,
  FileSpreadsheet,
  FileText,
  Lock,
  TriangleAlert,
  Upload,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  maxEvidenceFileBytes,
  supportedEvidenceExtensions,
  supportedEvidenceLabel,
} from '@/data/intake';
import { cn } from '@/lib/cn';
import { formatFileSize } from '@/lib/format';
import type { DraftEvidenceFile } from '@/types';
import { DURATION, EASE_OUT } from '@/lib/motion';

const ICON_BY_EXTENSION: Record<string, LucideIcon> = {
  pdf: FileText,
  doc: FileText,
  docx: FileText,
  txt: FileText,
  md: FileText,
  xls: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  csv: FileSpreadsheet,
  png: FileImage,
  jpg: FileImage,
  jpeg: FileImage,
};

function iconFor(name: string): LucideIcon {
  const extension = name.split('.').pop()?.toLowerCase() ?? '';
  return ICON_BY_EXTENSION[extension] ?? FileIcon;
}

export interface EvidenceDropzoneProps {
  files: DraftEvidenceFile[];
  errors: string[];
  onAdd: (files: File[]) => void;
  onRemove: (id: string) => void;
}

export function EvidenceDropzone({ files, errors, onAdd, onRemove }: EvidenceDropzoneProps) {
  const [isDragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const reduceMotion = useReducedMotion();

  const openPicker = () => inputRef.current?.click();

  const onPicked = (event: ChangeEvent<HTMLInputElement>) => {
    const picked = event.target.files;
    if (picked) onAdd(Array.from(picked));
    // Reset so re-picking the same file still fires a change.
    event.target.value = '';
  };

  const onDragEnter = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current += 1;
    setDragging(true);
  };

  const onDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const onDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragging(false);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = 0;
    setDragging(false);

    const dropped = event.dataTransfer ? Array.from(event.dataTransfer.files) : [];
    if (dropped.length > 0) onAdd(dropped);
  };

  return (
    <div className="space-y-4">
      <motion.div
        data-dragging={isDragging || undefined}
        onDragEnter={onDragEnter}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        animate={reduceMotion ? undefined : { scale: isDragging ? 1.008 : 1 }}
        transition={{ duration: DURATION.quick, ease: EASE_OUT }}
        className={cn(
          'rounded-xl border border-dashed p-8 text-center transition-colors duration-200',
          isDragging
            ? 'border-accent bg-panel-accent'
            : 'border-hairline-strong bg-surface-inset hover:border-accent-line',
        )}
      >
        <motion.span
          animate={reduceMotion ? undefined : { y: isDragging ? -3 : 0 }}
          transition={{ duration: DURATION.quick }}
          className={cn(
            'mx-auto flex size-11 items-center justify-center rounded-lg border transition-colors',
            isDragging
              ? 'border-accent-line bg-accent-soft text-accent-ink'
              : 'border-hairline bg-surface-raised text-ink-muted',
          )}
        >
          <Upload className="size-5" aria-hidden />
        </motion.span>

        <p className="mt-4 text-card-title text-ink">
          {isDragging ? 'Release to attach' : 'Drop your evidence here'}
        </p>
        <p className="mx-auto mt-2 max-w-md text-small text-ink-secondary">
          Drop reports, spreadsheets, PDFs, research, notes, or screenshots here.
        </p>

        <Button variant="secondary" size="sm" className="mt-5" onClick={openPicker}>
          Browse files
        </Button>

        <p className="numeric mt-4 text-micro text-ink-muted">
          {supportedEvidenceLabel} · up to {formatFileSize(maxEvidenceFileBytes)} each
        </p>

        <input
          ref={inputRef}
          type="file"
          multiple
          accept={supportedEvidenceExtensions.join(',')}
          onChange={onPicked}
          className="sr-only"
          aria-label="Attach evidence files"
        />
      </motion.div>

      {errors.length > 0 ? (
        <ul className="space-y-1.5">
          {errors.map((error) => (
            <li key={error} className="flex items-start gap-2 text-small text-danger-ink">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              {error}
            </li>
          ))}
        </ul>
      ) : null}

      {files.length > 0 ? (
        <div className="space-y-2">
          <AnimatePresence initial={false}>
            {files.map((file) => {
              const Icon = iconFor(file.name);

              return (
                <motion.div
                  key={file.id}
                  layout={!reduceMotion}
                  initial={reduceMotion ? undefined : { opacity: 0, y: 6 }}
                  animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                  transition={{ duration: DURATION.quick, ease: EASE_OUT }}
                  className="flex items-center gap-3 rounded-lg border border-hairline bg-surface-raised px-3.5 py-2.5"
                >
                  <Icon className="size-4 shrink-0 text-ink-muted" aria-hidden />
                  <span className="min-w-0 flex-1 truncate text-small text-ink">{file.name}</span>
                  <span className="numeric shrink-0 text-micro text-ink-muted">
                    {formatFileSize(file.size)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    iconOnly
                    leftIcon={X}
                    aria-label={`Remove ${file.name}`}
                    onClick={() => onRemove(file.id)}
                  />
                </motion.div>
              );
            })}
          </AnimatePresence>

          <p className="flex items-center gap-2 pt-1 text-micro text-ink-muted">
            <Lock className="size-3 shrink-0" aria-hidden />
            {files.length} file{files.length === 1 ? '' : 's'} held in this browser. Nothing is
            uploaded yet.
          </p>
        </div>
      ) : null}
    </div>
  );
}
