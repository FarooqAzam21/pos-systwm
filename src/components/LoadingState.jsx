export default function LoadingState({ label = 'Loading…' }) {
  return <div className="screen-loading"><span className="spinner" />{label}</div>
}
