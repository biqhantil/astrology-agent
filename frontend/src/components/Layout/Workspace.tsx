/* ── Main Workspace: Chart + Chat side by side ───────── */

import type { FC } from 'react';
import ChartController from '../Chart/ChartController';
import ChatPanel from '../Chat/ChatPanel';

/**
 * The main workspace splits the screen into two panels:
 * - Left: Chart workspace (ZodiacWheel, transits, etc.)
 * - Right: Chat panel (messages, input)
 *
 * On mobile (<768px), it stacks vertically.
 */
const Workspace: FC = () => {
  return (
    <div className="flex flex-col md:flex-row h-full overflow-hidden">
      {/* Left: Chart workspace */}
      <div className="w-full md:w-3/5 h-1/2 md:h-full overflow-auto border-r border-gray-800/50">
        <ChartController />
      </div>

      {/* Right: Chat panel */}
      <div className="w-full md:w-2/5 h-1/2 md:h-full overflow-hidden flex flex-col">
        <ChatPanel />
      </div>
    </div>
  );
};

export default Workspace;
