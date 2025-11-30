import React, { useState, useRef, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import LeftSidebar from '../components/agents/LeftSidebar';
import RightSidebar from '../components/agents/RightSidebar';

const AgentsLayout: React.FC = () => {
    // State for column widths and sidebar collapse
    const [leftWidth, setLeftWidth] = useState(260);
    const [rightWidth, setRightWidth] = useState(350);
    const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
    const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);

    // Resizing logic
    const isResizingLeft = useRef(false);
    const isResizingRight = useRef(false);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!containerRef.current) return;
            const containerRect = containerRef.current.getBoundingClientRect();

            if (isResizingLeft.current) {
                const newWidth = e.clientX - containerRect.left;
                if (newWidth > 200 && newWidth < 400) setLeftWidth(newWidth);
            }

            if (isResizingRight.current && !isRightSidebarCollapsed) {
                const newWidth = containerRect.right - e.clientX;
                if (newWidth > 300 && newWidth < 500) setRightWidth(newWidth);
            }
        };

        const handleMouseUp = () => {
            isResizingLeft.current = false;
            isResizingRight.current = false;
            document.body.style.cursor = 'default';
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isRightSidebarCollapsed]);

    // Toggle sidebars
    const toggleLeftSidebar = () => {
        setIsLeftSidebarCollapsed(!isLeftSidebarCollapsed);
    };

    const toggleRightSidebar = () => {
        setIsRightSidebarCollapsed(!isRightSidebarCollapsed);
    };

    return (
        <div ref={containerRef} className="flex h-screen bg-background overflow-hidden text-foreground font-sans">

            <LeftSidebar
                width={isLeftSidebarCollapsed ? 70 : leftWidth}
                onResizeStart={() => { isResizingLeft.current = true; document.body.style.cursor = 'col-resize'; }}
                isCollapsed={isLeftSidebarCollapsed}
                onToggleCollapse={toggleLeftSidebar}
            />

            {/* MAIN CONTENT AREA */}
            <main className="flex-1 overflow-y-auto relative h-full bg-background bg-noise">
                <Outlet />
            </main>

            <RightSidebar
                width={isRightSidebarCollapsed ? 70 : rightWidth}
                isCollapsed={isRightSidebarCollapsed}
                onToggleCollapse={toggleRightSidebar}
                onResizeStart={() => {
                    if (!isRightSidebarCollapsed) {
                        isResizingRight.current = true;
                        document.body.style.cursor = 'col-resize';
                    }
                }}
            />

        </div>
    );
};

export default AgentsLayout;
