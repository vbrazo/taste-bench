import type { EngagementEvent } from "@tastegraph/sdk";

export function EngagementStream({ events }: { events: EngagementEvent[] }) {
  const recent = [...events].slice(-40).reverse();
  return (
    <div className="panel">
      <div className="panel-head"><span>▾ ENGAGEMENT STREAM</span></div>
      <div className="stream" data-testid="engagement-stream">
        {recent.length === 0 && <div className="empty">No events yet.</div>}
        {recent.map((e, i) => (
          <div key={`${e.ts}-${i}`} className="stream-row">
            {e.assetId} · {e.action} · dwell {Math.round(e.dwellMs ?? 0)}ms
          </div>
        ))}
      </div>
    </div>
  );
}
