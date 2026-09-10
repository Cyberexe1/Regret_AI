import { useState } from 'react';
import { FlaskConical, Paperclip, Printer, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { evidenceApi } from '@/api';
import { EvidenceDropzone } from '@/components/intake/EvidenceDropzone';
import { Button, buttonClasses } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { ROUTES, analysisPath } from '@/data/navigation';
import { describeApiError } from '@/lib/apiError';
import { useEvidenceFiles } from '@/hooks/useEvidenceFiles';

export interface ReportActionsProps {
  decisionId: string;
  /** Called after at least one evidence file uploads successfully, so the
   * caller can refetch the decision's evidence list. */
  onEvidenceUploaded?: () => void;
}

export function ReportActions({ decisionId, onEvidenceUploaded }: ReportActionsProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const evidence = useEvidenceFiles();

  const secondary = buttonClasses({ variant: 'secondary', size: 'md' });

  const uploadAll = async () => {
    setIsUploading(true);
    setUploadError(null);
    let anySucceeded = false;

    for (const item of evidence.files) {
      try {
        await evidenceApi.uploadEvidence(decisionId, item.file);
        anySucceeded = true;
        evidence.removeFile(item.id);
      } catch (error) {
        setUploadError(describeApiError(error).message);
      }
    }

    setIsUploading(false);
    if (anySucceeded) onEvidenceUploaded?.();
  };

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <Link to={ROUTES.experiments} className={secondary}>
          <FlaskConical className="size-4" aria-hidden />
          Run Experiment
        </Link>

        <Button variant="secondary" leftIcon={Paperclip} onClick={() => setEvidenceOpen(true)}>
          Add Evidence
        </Button>

        <Link to={analysisPath(decisionId)} className={secondary}>
          <RefreshCw className="size-4" aria-hidden />
          Re-analyze
        </Link>

        {/* Uses the browser print dialog, which also covers save-as-PDF. */}
        <Button variant="secondary" leftIcon={Printer} onClick={() => window.print()}>
          Export Report
        </Button>
      </div>

      <Modal
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        title="Add evidence"
        description="Attach anything that would move one of the uncertainties above."
        size="lg"
        footer={
          <Button
            variant="primary"
            loading={isUploading}
            disabled={evidence.files.length === 0}
            onClick={() => void uploadAll()}
          >
            Upload
          </Button>
        }
      >
        <EvidenceDropzone
          files={evidence.files}
          errors={uploadError ? [...evidence.errors, uploadError] : evidence.errors}
          onAdd={evidence.addFiles}
          onRemove={evidence.removeFile}
        />
      </Modal>
    </>
  );
}
