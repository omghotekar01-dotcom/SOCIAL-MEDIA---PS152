import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ShieldCheck } from 'lucide-react';

type Props = { children: ReactNode };
type State = { error: Error | null };

export default class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Do not expose secrets or request payloads. This is intentionally limited to
    // the render error and React component stack for local developer debugging.
    console.error('NEXUS frontend render failure:', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="fatal-recovery" role="alert">
        <div className="fatal-recovery-card">
          <span className="fatal-recovery-icon"><AlertTriangle size={28} /></span>
          <div className="eyebrow">Controlled recovery</div>
          <h1>NEXUS hit a display error</h1>
          <p>The analytics backend and stored evidence are not deleted. Reload the interface to recover the current workspace.</p>
          <div className="fatal-recovery-note"><ShieldCheck size={16} /><span>No credentials or secret values are shown in this error screen.</span></div>
          <details>
            <summary>Technical detail</summary>
            <pre>{this.state.error.message}</pre>
          </details>
          <button className="btn btn-primary" onClick={() => window.location.reload()}><RefreshCw size={15} /> Reload NEXUS</button>
        </div>
      </main>
    );
  }
}
