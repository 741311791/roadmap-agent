'use client';

import { ReactNode } from 'react';
import { LeftSidebar } from './left-sidebar';
import { RightSidebar } from './right-sidebar';

interface AppShellProps {
  children: ReactNode;
  showRightSidebar?: boolean;
}

/**
 * AppShell - The main application layout with three-column structure
 * 
 * Layout:
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ LeftSidebar │          Main Content           │   RightSidebar  │
 * │   (260px)   │           (flex-1)              │     (350px)     │
 * └─────────────────────────────────────────────────────────────────┘
 */
export function AppShell({ children, showRightSidebar = true }: AppShellProps) {
  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground font-sans">
      {/* Left Sidebar - Navigation */}
      <LeftSidebar />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto relative h-full bg-background bg-noise">
        {children}
      </main>

      {/* Right Sidebar - AI Assistant */}
      {showRightSidebar && <RightSidebar />}
    </div>
  );
}

