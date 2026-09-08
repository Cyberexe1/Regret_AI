import { useCallback, useState } from 'react';
import { maxEvidenceFileBytes, supportedEvidenceExtensions } from '@/data/intake';
import { formatFileSize } from '@/lib/format';
import type { DraftEvidenceFile } from '@/types';

let fileSequence = 0;

function nextFileId(): string {
  fileSequence += 1;
  return `evd-${Date.now().toString(36)}-${fileSequence}`;
}

function hasSupportedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return supportedEvidenceExtensions.some((extension) => lower.endsWith(extension));
}

export interface EvidenceFiles {
  files: DraftEvidenceFile[];
  /** Rejection messages from the most recent attempt. */
  errors: string[];
  addFiles: (files: File[]) => void;
  removeFile: (id: string) => void;
}

/**
 * Attachment list plus the client-side rules around it. Shared by decision
 * intake and the report's evidence dialog so validation lives in one place.
 *
 * Files never leave the browser; only metadata is retained.
 */
export function useEvidenceFiles(): EvidenceFiles {
  const [files, setFiles] = useState<DraftEvidenceFile[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const addFiles = useCallback((incoming: File[]) => {
    const accepted: DraftEvidenceFile[] = [];
    const rejected: string[] = [];

    for (const file of incoming) {
      if (!hasSupportedExtension(file.name)) {
        rejected.push(`${file.name} is not a supported file type.`);
        continue;
      }
      if (file.size > maxEvidenceFileBytes) {
        rejected.push(
          `${file.name} is ${formatFileSize(file.size)}, over the ${formatFileSize(
            maxEvidenceFileBytes,
          )} limit.`,
        );
        continue;
      }
      accepted.push({
        id: nextFileId(),
        name: file.name,
        size: file.size,
        mimeType: file.type,
      });
    }

    setErrors(rejected);
    if (accepted.length > 0) setFiles((current) => [...current, ...accepted]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles((current) => current.filter((file) => file.id !== id));
  }, []);

  return { files, errors, addFiles, removeFile };
}
