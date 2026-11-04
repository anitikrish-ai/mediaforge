import { GlassSegmented } from "@zakisheriff/liquid-glass";

/** GlassSegmented works on indices; every tool panel here thinks in string
 * values, so this wrapper does the index<->value translation once. */
export default function SegmentedField({ options, value, onChange, size }) {
  const index = Math.max(0, options.indexOf(value));
  return (
    <GlassSegmented
      // Remount when the option set itself changes shape (e.g. loaded async
      // after mount) — the glass control measures pill widths once on mount
      // and won't reflow correctly if the options grow in place.
      key={options.join("|")}
      options={options}
      value={index}
      onChange={(i) => onChange(options[i])}
      size={size}
    />
  );
}
