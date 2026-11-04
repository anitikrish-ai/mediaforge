export default function ProgressBar({ progress = 0, message = "" }) {
  return (
    <div className="progressbar">
      <div className="progressbar__track">
        <div className="progressbar__fill" style={{ width: `${Math.max(2, progress)}%` }} />
      </div>
      <div className="progressbar__label">
        {message || `${progress.toFixed(0)}%`}
      </div>
    </div>
  );
}
