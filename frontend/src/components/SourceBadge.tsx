const SIMULATED = "SIMULATED";

interface Props {
  sources: string[];
  className?: string;
}

export function SourceBadge({ sources, className = "" }: Props) {
  if (sources.length === 0) return null;

  const realSources = Array.from(new Set(sources.filter((s) => s !== SIMULATED)));
  const isLive = realSources.length > 0;
  const label = isLive ? `Live · ${realSources.join(", ")}` : "Simulated";
  const title = isLive
    ? `Includes real scraped prices from ${realSources.join(", ")}`
    : "No live scraper covers this segment yet — synthetic data generated to demonstrate the pipeline";

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full whitespace-nowrap ${
        isLive ? "text-up bg-up-bg" : "text-muted bg-subtle/60"
      } ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-up live-dot" : "bg-muted"}`} />
      {label}
    </span>
  );
}
