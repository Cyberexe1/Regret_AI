import { useState } from 'react';
import { FlaskConical, Paperclip, Printer, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EvidenceDropzone } from '@/components/intake/EvidenceDropzone';
import { Button, buttonClasses } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { ROUTES } from '@/data/navigation';
import { useEvidenceFiles } from '@/hooks/useEvidenceFiles';

export function ReportActions() {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidence = useEvidenceFiles();

  const secondary = buttonClasses({ variant: 'secondary', size: 'md' });

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <Link to={ROUTES.experiments} className={secondary}>
          <FlaskConical className="size-4" aria-hidden />
          Run Experiment
        </Link>

        <Button
          variant="secondary"
          leftIcon={Paperclip}
          onClick={() => setEvidenceOpen(true)}
        >
          Add Evidence
        </Button>

        <Link to={ROUTES.analysis} className={secondary}>
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
          <Button variant="primary" onClick={() => setEvidenceOpen(false)}>
            Done
          </Button>
        }
      >
        <EvidenceDropzone
          files={evidence.files}
          errors={evidence.errors}
          onAdd={evidence.addFiles}
          onRemove={evidence.removeFile}
        />
      </Modal>
    </>
  );
}
