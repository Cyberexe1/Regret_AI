import { useState } from 'react';
import { AtSign, Info, User } from 'lucide-react';
import { PageContainer } from '@/components/layout/PageContainer';
import {
  DangerZone,
  SettingRow,
  SettingsSection,
  SubscriptionCard,
  ThemePicker,
} from '@/components/settings';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';
import { riskToleranceOptions } from '@/data/intake';
import { useApiConnection } from '@/hooks/useApiConnection';
import { useWorkspaceSettings, type BooleanSettingKey } from '@/hooks/useWorkspaceSettings';

const CURRENCY_OPTIONS = [
  { value: 'INR', label: 'INR — Indian rupee' },
  { value: 'USD', label: 'USD — US dollar' },
];

export function SettingsPage() {
  const { settings, set, toggle } = useWorkspaceSettings();
  const [upgradeNotice, setUpgradeNotice] = useState(false);
  const connection = useApiConnection();

  /** Every switch row shares this shape. */
  const switchRow = (key: BooleanSettingKey, label: string, description: string) => (
    <SettingRow
      key={key}
      label={label}
      description={description}
      control={
        <Switch checked={settings[key]} onChange={() => toggle(key)} label={label} />
      }
    />
  );

  return (
    <PageContainer
      eyebrow="Workspace"
      title="Settings"
      description="Your profile, analysis defaults and how the engine reports back to you."
      width="narrow"
    >
      <div className="space-y-5">
        <SettingsSection title="Backend connection" description="Where this app is sending its requests.">
          <SettingRow
            label="API base URL"
            control={<span className="numeric text-small text-ink-secondary">{connection.baseUrl}</span>}
          />
          <SettingRow
            label="Status"
            control={
              connection.status === 'loading' ? (
                <Badge tone="neutral" size="sm" dot>
                  Checking…
                </Badge>
              ) : connection.status === 'error' ? (
                <Badge tone="danger" size="sm" dot>
                  Unreachable
                </Badge>
              ) : (
                <Badge tone={connection.readiness?.status === 'ready' ? 'success' : 'warning'} size="sm" dot>
                  {connection.readiness?.status === 'ready' ? 'Ready' : 'Degraded'}
                </Badge>
              )
            }
          />
          {connection.readiness ? (
            <SettingRow
              label="Dependencies"
              control={
                <div className="flex flex-wrap justify-end gap-1.5">
                  {connection.readiness.dependencies.map((dep) => (
                    <Badge
                      key={dep.name}
                      tone={dep.status === 'ok' ? 'success' : dep.required ? 'danger' : 'neutral'}
                      size="sm"
                      variant="outline"
                    >
                      {dep.name}: {dep.status}
                    </Badge>
                  ))}
                </div>
              }
            />
          ) : null}
        </SettingsSection>

        <SettingsSection title="Profile" description="How you appear inside the workspace.">
          <div className="flex items-center gap-4 px-5 py-5 md:px-6">
            <Avatar name={settings.name} size="lg" />
            <div className="min-w-0">
              <p className="truncate text-card-title text-ink">{settings.name}</p>
              <p className="truncate text-small text-ink-muted">{settings.email}</p>
            </div>
          </div>

          <SettingRow
            label="Name"
            control={
              <Input
                aria-label="Name"
                icon={User}
                value={settings.name}
                onChange={(event) => set('name', event.target.value)}
                className="sm:w-64"
              />
            }
          />
          <SettingRow
            label="Email"
            control={
              <Input
                aria-label="Email"
                type="email"
                icon={AtSign}
                value={settings.email}
                onChange={(event) => set('email', event.target.value)}
                className="sm:w-64"
              />
            }
          />
        </SettingsSection>

        <SettingsSection
          title="Preferences"
          description="Applied as defaults when you start a new decision."
        >
          <SettingRow
            label="Default risk tolerance"
            description="Sets how hard the engine argues against the downside."
            control={
              <Select
                aria-label="Default risk tolerance"
                options={riskToleranceOptions.map((option) => ({
                  value: option.value,
                  label: option.label,
                }))}
                value={settings.defaultRiskTolerance}
                onChange={(event) =>
                  set('defaultRiskTolerance', event.target.value as typeof settings.defaultRiskTolerance)
                }
                className="sm:w-56"
              />
            }
          />
          <SettingRow
            label="Default currency"
            description="Used for budgets, experiment costs and thresholds."
            control={
              <Select
                aria-label="Default currency"
                options={CURRENCY_OPTIONS}
                value={settings.defaultCurrency}
                onChange={(event) =>
                  set('defaultCurrency', event.target.value as typeof settings.defaultCurrency)
                }
                className="sm:w-56"
              />
            }
          />
        </SettingsSection>

        <SettingsSection
          title="Analysis preferences"
          description="What the engine includes in a stress test."
        >
          {switchRow(
            'showUncertaintyExplanations',
            'Show uncertainty explanations',
            'Include why each uncertainty matters, not just its score.',
          )}
          {switchRow(
            'showExperimentRecommendations',
            'Show experimental recommendations',
            'Propose the cheapest test that would change your mind.',
          )}
          {switchRow(
            'saveDecisionHistory',
            'Save decision history',
            'Keep analysed decisions so you can compare outcomes later.',
          )}
        </SettingsSection>

        <SettingsSection title="Notifications" description="When the engine should reach you.">
          {switchRow(
            'notifyAnalysisComplete',
            'Decision analysis complete',
            'Tells you when a stress test has finished running.',
          )}
          {switchRow(
            'notifyExperimentMilestone',
            'Experiment milestone',
            'Alerts you when an experiment crosses or misses a threshold.',
          )}
          {switchRow(
            'notifyWeeklyReview',
            'Weekly decision review',
            'A Monday summary of open decisions and unresolved uncertainties.',
          )}
        </SettingsSection>

        <SettingsSection title="Appearance">
          <SettingRow
            label="Theme"
            description="Choose how the interface should follow your system."
            control={<ThemePicker value={settings.theme} onChange={(theme) => set('theme', theme)} />}
            stacked
          />
        </SettingsSection>

        <SettingsSection title="Subscription" description="Plan and monthly analysis allowance.">
          <SubscriptionCard onUpgrade={() => setUpgradeNotice(true)} />
          {upgradeNotice ? (
            <p className="flex items-start gap-2 px-5 py-4 text-small text-ink-secondary md:px-6">
              <Info className="mt-0.5 size-3.5 shrink-0 text-info-ink" aria-hidden />
              Billing is not connected in this build, so there is no plan to move to yet.
            </p>
          ) : null}
        </SettingsSection>

        <SettingsSection
          title="Danger zone"
          description="Irreversible actions, once there is something to reverse."
          tone="danger"
        >
          <DangerZone />
        </SettingsSection>

        <p className="px-1 text-small text-ink-muted">
          Preferences are held in this browser only. Nothing is saved to an account yet.
        </p>
      </div>
    </PageContainer>
  );
}
