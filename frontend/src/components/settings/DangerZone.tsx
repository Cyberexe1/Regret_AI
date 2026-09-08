import { useState } from 'react';
import { Info, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { decisions } from '@/data/decisions';
import { experiments } from '@/data/experiments';

/**
 * Deletion is deliberately inert. The modal states plainly that nothing is
 * removed, so the confirm button is not lying about what it does.
 */
export function DangerZone() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  const onConfirm = () => {
    setConfirmOpen(false);
    setAcknowledged(true);
  };

  return (
    <div className="px-5 py-5 md:px-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-small font-medium text-ink">Delete all decision history</p>
          <p className="mt-1 max-w-md text-small text-ink-secondary">
            Removes every decision, analysis and experiment in this workspace. This cannot be
            undone once there is a backend to undo it against.
          </p>
        </div>

        <Button variant="danger" size="md" leftIcon={Trash2} onClick={() => setConfirmOpen(true)}>
          Delete history
        </Button>
      </div>

      {acknowledged ? (
        <p className="mt-4 flex items-start gap-2 rounded-lg border border-hairline bg-surface-inset px-4 py-3 text-small text-ink-secondary">
          <Info className="mt-0.5 size-3.5 shrink-0 text-info-ink" aria-hidden />
          Nothing was deleted. This prototype has no backend, so your decisions are untouched.
        </p>
      ) : null}

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Delete all decision history?"
        description="This would permanently remove everything in the workspace."
        size="sm"
        dismissOnBackdrop={false}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" leftIcon={Trash2} onClick={onConfirm}>
              Delete everything
            </Button>
          </>
        }
      >
        <ul className="space-y-2">
          <li className="flex items-baseline justify-between gap-4 text-small">
            <span className="text-ink-secondary">Decisions</span>
            <span className="numeric font-medium text-ink">{decisions.length}</span>
          </li>
          <li className="flex items-baseline justify-between gap-4 text-small">
            <span className="text-ink-secondary">Experiments</span>
            <span className="numeric font-medium text-ink">{experiments.length}</span>
          </li>
        </ul>

        <p className="mt-5 rounded-lg border border-info-line bg-panel-info px-4 py-3 text-small text-ink-secondary">
          Nothing will actually be deleted. This build has no backend, so confirming only
          demonstrates the flow.
        </p>
      </Modal>
    </div>
  );
}
