/* ── Top-level App Shell ─────────────────────────────── */

import type { FC, ReactNode } from 'react';
import TopBar from './TopBar';
import Workspace from './Workspace';

interface AppShellProps {
  /** Main workspace content (chart + chat panel) */
  children?: ReactNode;
}

/**
 * The top-level layout container.
 *
 * Structure:
 * ┌──────────────────────────────────┐
 * │            TopBar                 │
 * ├──────────────────────────────────┤
 * │           Workspace               │
 * │  ┌──────────────┬──────────────┐  │
 * │  │   Chart      │   Chat       │  │
 * │  │   Workspace  │   Panel      │  │
 * │  └──────────────┴──────────────┘  │
 * └──────────────────────────────────┘
 */
const AppShell: FC<AppShellProps> = ({ children }) => {
  return (
    <div className="h-screen flex flex-col bg-gray-950 overflow-hidden">
      {/* Top navigation bar */}
      <TopBar />

      {/* Main workspace area */}
      <main className="flex-1 overflow-hidden">
        {children ?? <Workspace />}
      </main>
    </div>
  );
};

export default AppShell;
