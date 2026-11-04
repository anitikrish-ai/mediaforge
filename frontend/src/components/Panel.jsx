import { GlassCard } from "@zakisheriff/liquid-glass";

/** Standard glass panel wrapper used by every tool so the dashboard feels unified. */
export default function Panel({ title, subtitle, children, actions }) {
  return (
    <GlassCard padding="24px" radius="24px" className="panel">
      <div className="panel__header">
        <div>
          <h2 className="panel__title">{title}</h2>
          {subtitle && <p className="panel__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="panel__actions">{actions}</div>}
      </div>
      <div className="panel__body">{children}</div>
    </GlassCard>
  );
}
