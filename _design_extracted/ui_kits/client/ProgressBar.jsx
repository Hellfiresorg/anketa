// Progress bar — unrounded flush-top strip
function ProgressBar({ current = 1, total = 10 }) {
  return (
    <div className="client-progress-track">
      <div
        className="client-progress-fill"
        style={{ width: `${(current / total) * 100}%` }}
      />
    </div>
  );
}
window.ProgressBar = ProgressBar;
