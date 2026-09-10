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

/**
 * A locally-attached evidence file, still holding the real browser `File`
 * so it can actually be uploaded (multipart/form-data) once the decision
 * this draft belongs to has a real id - see `useDecisionSubmission`.
 * `DraftEvidenceFile` (metadata only) is derived from this for display and
 * for the parts of the UI that only need to show name/size.
 */
export interface DraftEvidenceFileWithBlob extends DraftEvidenceFile {
  file: File;
}

export interface EvidenceFiles {
  files: DraftEvidenceFileWithBlob[];
  /** Rejection messages from the most recent attempt. */
  errors: string[];
  addFiles: (files: File[]) => void;
  removeFile: (id: string) => void;
}

/**
 * Attachment list plus the client-side rules around it. Shared by decision
 * intake and the report's evidence dialog so validation lives in one place.
 *
 * Files stay in the browser until the decision they belong to has a real
 * id (submission is a two-step "create decision, then upload its
 * evidence" flow - see `useDecisionSubmission`) - this hook only holds
 * them locally and validates them client-side in the meantime. Client-side
 * checks here are a UX convenience only; the backend independently
 * re-validates extension/size/content on upload and is the source of
 * truth for what's actually accepted.
 */
export function useEvidenceFiles(): EvidenceFiles {
  const [files, setFiles] = useState<DraftEvidenceFileWithBlob[]>([]);
  const [errors, setErrors] = useState<string[]>([]);

  const addFiles = useCallback((incoming: File[]) => {
    const accepted: DraftEvidenceFileWithBlob[] = [];
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
        file,
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
