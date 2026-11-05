/** A wrapping row of plain pill buttons for picking one of several string
 * options. Used everywhere instead of the liquid-glass GlassSegmented
 * control, which has a fixed intrinsic width and doesn't wrap — with seven
 * image filters or several background-removal models, that overflowed its
 * container every time. Plain buttons wrap, which this never breaks on. */
export default function PillField({ options, value, onChange, labelFor }) {
  return (
    <div className="pill-list">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          className={`pill ${value === opt ? "pill--active" : ""}`}
          onClick={() => onChange(opt)}
        >
          {labelFor ? labelFor(opt) : opt}
        </button>
      ))}
    </div>
  );
}
