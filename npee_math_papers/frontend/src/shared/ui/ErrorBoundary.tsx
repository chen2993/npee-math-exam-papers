/**
 * Route-level error boundary.
 *
 * A rendering exception in one page must not blank the whole console. The
 * boundary keeps the shell (sidebar, header) alive and shows the error plus a
 * retry action, matching refine's "error pages are first-class" approach.
 */

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "./Button";

interface Props {
  children: ReactNode;
  /** Reset the boundary when this changes (e.g. the current path). */
  resetKey?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(previous: Props): void {
    if (previous.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Keep the component stack in the console for debugging; the UI stays terse.
    console.error("NPEE 页面渲染失败", error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="error-panel surface">
        <span className="error-panel-icon">
          <AlertTriangle size={22} />
        </span>
        <h3>此页面渲染失败</h3>
        <p>{error.message || "未知错误"}</p>
        <div className="error-panel-actions">
          <Button icon={<RefreshCw size={15} />} onClick={() => this.setState({ error: null })}>
            重试
          </Button>
          <Button variant="primary" onClick={() => window.location.reload()}>
            重新载入
          </Button>
        </div>
      </div>
    );
  }
}
