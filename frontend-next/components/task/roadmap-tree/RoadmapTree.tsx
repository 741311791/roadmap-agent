'use client';

/**
 * RoadmapTree - 动态路线图树组件
 * 
 * 水平树状图展示路线图结构：Stage -> Module -> Concept
 * 
 * 功能:
 * - SVG 贝塞尔曲线连接线
 * - 节点展开/折叠
 * - 节点状态可视化
 * - 点击查看详情
 * - 全屏模式
 * - 滚动支持
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { 
  Maximize2, 
  Minimize2, 
  Loader2, 
  ChevronsRight, 
  ChevronsDown, 
  Filter, 
  History,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger, 
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuItem
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

import { TreeNode } from './TreeNode';
import { TreeConnector } from './TreeConnector';
import { NodeDetailPopover } from './NodeDetailPopover';
import { useTreeLayout, getDefaultExpansionState } from './useTreeLayout';
import type {
  RoadmapTreeProps,
  TreeNodeData,
  ExpansionState,
} from './types';
import { roadmapsApi, type EditHistoryVersion } from '@/lib/api/endpoints/roadmaps';

/**
 * 编辑模式蒙版组件（简化版）
 * 
 * 显示简单的加载状态蒙版，提示用户路线图正在更新中
 */
function EditingOverlay() {
  return (
    <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-40 flex items-center justify-center rounded-lg">
      <div className="text-center space-y-3">
        <Loader2 className="w-10 h-10 text-sage-600 animate-spin mx-auto" />
        <p className="text-sm text-gray-600">Updating roadmap structure...</p>
      </div>
    </div>
  );
}

/**
 * 树视图内容（可在普通模式和全屏模式复用）
 */
interface TreeViewContentProps {
  nodes: TreeNodeData[];
  connections: { id: string; fromNodeId: string; toNodeId: string; fromPosition: { x: number; y: number }; toPosition: { x: number; y: number } }[];
  totalWidth: number;
  totalHeight: number;
  selectedNode: TreeNodeData | null;
  onNodeClick: (node: TreeNodeData) => void;
  onToggleExpand: (nodeId: string) => void;
  isEditing?: boolean;
  taskId?: string;
}

function TreeViewContent({
  nodes,
  connections,
  totalWidth,
  totalHeight,
  selectedNode,
  onNodeClick,
  onToggleExpand,
  isEditing,
  taskId,
}: TreeViewContentProps) {
  return (
    <div
      className="relative"
      style={{
        width: totalWidth,
        height: totalHeight,
        minWidth: '100%',
      }}
    >
      {/* SVG 连接线层 */}
      <TreeConnector
        connections={connections}
        width={totalWidth}
        height={totalHeight}
      />
      
      {/* 节点层 */}
      {nodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          onClick={onNodeClick}
          onToggleExpand={onToggleExpand}
          isSelected={selectedNode?.id === node.id}
        />
      ))}
      
      {/* 编辑模式蒙版 */}
      {isEditing && <EditingOverlay />}
    </div>
  );
}

export function RoadmapTree({
  stages,
  showStartNode = false,
  isEditing = false,
  taskId,
  roadmapId,
  showHistoryButton = false,
  modifiedNodeIds = [],
  loadingConceptIds = [],
  failedConceptIds = [],
  partialFailedConceptIds = [],
  onNodeClick,
  userPreferences,
  onRetrySuccess,
  className,
}: RoadmapTreeProps) {
  // 展开状态
  const [expansionState, setExpansionState] = useState<ExpansionState>(() =>
    getDefaultExpansionState(stages)
  );
  
  // 选中的节点（用于显示详情）
  const [selectedNode, setSelectedNode] = useState<TreeNodeData | null>(null);
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  
  // 全屏模式
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // 容器引用
  const containerRef = useRef<HTMLDivElement>(null);
  
  // 状态筛选
  const [statusFilter, setStatusFilter] = useState<Set<string>>(new Set(['completed', 'loading', 'pending', 'failed', 'partial_failure', 'modified']));
  
  // 历史版本相关状态
  const [historyVersions, setHistoryVersions] = useState<EditHistoryVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [showHistoryDropdown, setShowHistoryDropdown] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // 获取历史版本列表
  useEffect(() => {
    if (!showHistoryButton || !taskId || !roadmapId) return;
    
    const fetchHistory = async () => {
      setHistoryLoading(true);
      try {
        const history = await roadmapsApi.getFullEditHistory(taskId, roadmapId);
        setHistoryVersions(history.versions);
      } catch (error) {
        console.error('Failed to fetch edit history:', error);
      } finally {
        setHistoryLoading(false);
      }
    };
    
    fetchHistory();
  }, [taskId, roadmapId, showHistoryButton]);
  
  // 版本选择处理
  const handleVersionSelect = useCallback((versionNumber: number) => {
    setSelectedVersion(versionNumber);
    setShowHistoryDropdown(false);
  }, []);
  
  // 重置到当前版本
  const handleResetToCurrentVersion = useCallback(() => {
    setSelectedVersion(null);
  }, []);
  
  // 根据选中的版本确定要显示的stages和modifiedNodeIds
  const { displayStages, displayModifiedNodeIds } = useMemo(() => {
    if (selectedVersion === null) {
      // 显示当前版本
      return {
        displayStages: stages,
        displayModifiedNodeIds: modifiedNodeIds
      };
    }
    
    // 显示历史版本
    const version = historyVersions.find(v => v.version === selectedVersion);
    if (!version) {
      return {
        displayStages: stages,
        displayModifiedNodeIds: modifiedNodeIds
      };
    }
    
    return {
      displayStages: version.framework_data.stages || [],
      displayModifiedNodeIds: version.modified_node_ids
    };
  }, [selectedVersion, historyVersions, stages, modifiedNodeIds]);
  
  // 计算布局
  const { nodes, connections, totalWidth, totalHeight } = useTreeLayout({
    stages: displayStages,
    expansionState,
    modifiedNodeIds: displayModifiedNodeIds,
    loadingConceptIds,
    failedConceptIds,
    partialFailedConceptIds,
    showStartNode,
  });
  
  // 应用状态筛选
  const filteredNodes = useMemo(() => {
    if (statusFilter.size === 6) return nodes; // 全部显示
    return nodes.filter(node => statusFilter.has(node.status));
  }, [nodes, statusFilter]);
  
  // 根据筛选后的节点过滤连接线
  const filteredConnections = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map(n => n.id));
    return connections.filter(conn => 
      visibleNodeIds.has(conn.fromNodeId) && visibleNodeIds.has(conn.toNodeId)
    );
  }, [connections, filteredNodes]);
  
  // 切换筛选状态
  const toggleStatusFilter = useCallback((status: string) => {
    setStatusFilter(prev => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  }, []);
  
  // 筛选器是否激活（不是全部显示）
  const isFilterActive = statusFilter.size < 6;
  
  // 计算整体统计信息
  const stats = useMemo(() => {
    // 只统计 concept 级别的节点
    const conceptNodes = nodes.filter(node => node.type === 'concept');
    const total = conceptNodes.length;
    const completed = conceptNodes.filter(node => node.status === 'completed').length;
    const loading = conceptNodes.filter(node => node.status === 'loading').length;
    const pending = conceptNodes.filter(node => node.status === 'pending').length;
    const failed = conceptNodes.filter(node => node.status === 'failed').length;
    const partialFailure = conceptNodes.filter(node => node.status === 'partial_failure').length;
    const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    return {
      total,
      completed,
      loading,
      pending,
      failed,
      partialFailure,
      progress,
    };
  }, [nodes]);
  
  // 当 stages 变化时，重置展开状态
  useEffect(() => {
    setExpansionState(getDefaultExpansionState(stages));
  }, [stages]);
  
  // 检查是否全部展开
  const allExpanded = useMemo(() => {
    // 获取所有可展开的节点ID（stage和module）
    const expandableNodeIds: string[] = [];
    stages.forEach(stage => {
      expandableNodeIds.push(stage.stage_id);
      stage.modules.forEach(module => {
        expandableNodeIds.push(module.module_id);
      });
    });
    // 检查是否全部展开
    return expandableNodeIds.every(id => expansionState[id] === true);
  }, [stages, expansionState]);
  
  // 切换节点展开状态
  const handleToggleExpand = useCallback((nodeId: string) => {
    setExpansionState((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  }, []);
  
  // 全部展开/折叠
  const handleToggleAll = useCallback(() => {
    const expandableNodeIds: string[] = [];
    stages.forEach(stage => {
      expandableNodeIds.push(stage.stage_id);
      stage.modules.forEach(module => {
        expandableNodeIds.push(module.module_id);
      });
    });
    
    const newState: ExpansionState = {};
    expandableNodeIds.forEach(id => {
      newState[id] = !allExpanded;
    });
    
    setExpansionState(newState);
  }, [stages, allExpanded]);
  
  // 节点点击处理
  const handleNodeClick = useCallback((node: TreeNodeData) => {
    setSelectedNode(node);
    setIsPopoverOpen(true);
    onNodeClick?.(node);
  }, [onNodeClick]);
  
  // 关闭详情弹出层
  const handleClosePopover = useCallback(() => {
    setIsPopoverOpen(false);
    // 延迟清除选中状态，让动画完成
    setTimeout(() => setSelectedNode(null), 200);
  }, []);
  
  // 空状态
  if (!stages || stages.length === 0) {
    return (
      <div className={cn('flex items-center justify-center h-40 text-muted-foreground', className)}>
        No roadmap data available
      </div>
    );
  }
  
  return (
    <>
      {/* 主容器 */}
      <div
        ref={containerRef}
        className={cn(
          'relative w-full',
          className,
        )}
      >
        {/* 整体进度条和统计 - 集成工具栏 */}
        <div className="px-4 pt-4 pb-2 border-b">
          {/* 版本查看提示 Banner */}
          {selectedVersion !== null && (
            <div className="mb-3 px-3 py-2 bg-sage-50 border border-sage-200 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs">
                <History className="w-3.5 h-3.5 text-sage-600" />
                <span className="text-sage-700 font-medium">
                  Viewing Version {selectedVersion}
                </span>
                <span className="text-muted-foreground">
                  {historyVersions.find(v => v.version === selectedVersion)?.created_at 
                    ? `(${new Date(historyVersions.find(v => v.version === selectedVersion)!.created_at).toLocaleDateString()})`
                    : ''}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetToCurrentVersion}
                className="h-6 text-xs gap-1"
              >
                Back to Current
              </Button>
            </div>
          )}
          
          {/* 标题栏 */}
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-muted-foreground text-xs">Overall Progress</span>
            <span className="font-semibold text-sage-700 text-xs">{stats.progress}%</span>
          </div>
          
          {/* 进度条 */}
          <Progress value={stats.progress} className="h-1.5 mb-2" />
          
          {/* 统计信息和工具栏按钮 */}
          <div className="flex items-center justify-between">
            {/* 统计信息 */}
            <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-sage-500" />
                {stats.completed} Completed
              </span>
              {stats.loading > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-sage-400 animate-pulse" />
                  {stats.loading} In Progress
                </span>
              )}
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-300" />
                {stats.pending} Pending
              </span>
              {stats.failed > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  {stats.failed} Failed
                </span>
              )}
              {stats.partialFailure > 0 && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  {stats.partialFailure} Partial
                </span>
              )}
            </div>
            
            {/* 工具栏按钮 */}
            <div className="flex items-center gap-1">
              <TooltipProvider delayDuration={300}>
                {/* 状态筛选下拉菜单 */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant={isFilterActive ? "secondary" : "ghost"}
                      size="sm"
                      className={cn("h-7 gap-1 px-2", isFilterActive && "bg-sage-100 hover:bg-sage-200")}
                    >
                      <Filter className="w-3.5 h-3.5" />
                      <span className="text-xs">Filter</span>
                      {isFilterActive && (
                        <span className="ml-0.5 text-[10px] font-medium bg-sage-600 text-white rounded-full w-4 h-4 flex items-center justify-center">
                          {statusFilter.size}
                        </span>
                      )}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuLabel className="text-xs">Filter by Status</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('completed')}
                      onCheckedChange={() => toggleStatusFilter('completed')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-sage-500" />
                        Completed
                      </span>
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('loading')}
                      onCheckedChange={() => toggleStatusFilter('loading')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-sage-400 animate-pulse" />
                        Loading
                      </span>
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('pending')}
                      onCheckedChange={() => toggleStatusFilter('pending')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-gray-300" />
                        Pending
                      </span>
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('failed')}
                      onCheckedChange={() => toggleStatusFilter('failed')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-red-400" />
                        Failed
                      </span>
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('partial_failure')}
                      onCheckedChange={() => toggleStatusFilter('partial_failure')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        Partial Failure
                      </span>
                    </DropdownMenuCheckboxItem>
                    <DropdownMenuCheckboxItem
                      checked={statusFilter.has('modified')}
                      onCheckedChange={() => toggleStatusFilter('modified')}
                      className="text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-cyan-400" />
                        Modified
                      </span>
                    </DropdownMenuCheckboxItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                
                {/* 历史版本按钮 */}
                {showHistoryButton && taskId && roadmapId && (
                  <DropdownMenu open={showHistoryDropdown} onOpenChange={setShowHistoryDropdown}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            disabled={historyLoading}
                          >
                            {historyLoading ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <History className="w-3.5 h-3.5" />
                            )}
                          </Button>
                        </DropdownMenuTrigger>
                      </TooltipTrigger>
                      <TooltipContent side="left" className="text-xs">
                        View History
                      </TooltipContent>
                    </Tooltip>
                    <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
                      <DropdownMenuLabel className="text-xs">Version History</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {historyVersions.length === 0 ? (
                        <div className="px-2 py-4 text-center text-xs text-muted-foreground">
                          {historyLoading ? 'Loading...' : 'No edit history available'}
                        </div>
                      ) : (
                        historyVersions.map((version) => (
                          <DropdownMenuItem
                            key={version.version}
                            onClick={() => handleVersionSelect(version.version)}
                            className={cn(
                              'cursor-pointer',
                              selectedVersion === version.version && 'bg-sage-100'
                            )}
                          >
                            <div className="flex flex-col gap-1 w-full">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-xs">
                                  Version {version.version}
                                  {version.version === historyVersions.length && ' (Current)'}
                                </span>
                                <span className="text-[10px] text-muted-foreground">
                                  {new Date(version.created_at).toLocaleDateString()}
                                </span>
                              </div>
                              <p className="text-[10px] text-muted-foreground line-clamp-2">
                                {version.modification_summary}
                              </p>
                              {version.modified_node_ids.length > 0 && (
                                <span className="text-[10px] text-cyan-600">
                                  {version.modified_node_ids.length} nodes modified
                                </span>
                              )}
                            </div>
                          </DropdownMenuItem>
                        ))
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
                
                {/* 全部展开/折叠按钮 */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={handleToggleAll}
                    >
                      {allExpanded ? (
                        <ChevronsRight className="w-4 h-4" />
                      ) : (
                        <ChevronsDown className="w-4 h-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="text-xs">
                    {allExpanded ? 'Collapse All' : 'Expand All'}
                  </TooltipContent>
                </Tooltip>
                
                {/* 全屏按钮 */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={() => setIsFullscreen(true)}
                    >
                      <Maximize2 className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left" className="text-xs">
                    Fullscreen
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </div>
         
         {/* 内容区域 - 自适应高度，支持水平滚动 */}
         <div className="w-full overflow-x-auto">
         <div className="p-4">
            <TreeViewContent
              nodes={filteredNodes}
              connections={filteredConnections}
              totalWidth={totalWidth}
              totalHeight={totalHeight}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
              onToggleExpand={handleToggleExpand}
              isEditing={isEditing}
              taskId={taskId}
            />
          </div>
         </div>
        
        {/* 节点详情弹出层 */}
        <NodeDetailPopover
          node={selectedNode}
          isOpen={isPopoverOpen}
          onClose={handleClosePopover}
          anchorPosition={selectedNode?.position ? {
            x: selectedNode.position.x,
            y: selectedNode.position.y,
          } : undefined}
          roadmapId={roadmapId}
          userPreferences={userPreferences}
          onRetrySuccess={onRetrySuccess}
        />
      </div>
      
      {/* 全屏对话框 */}
      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-[95vw] max-h-[95vh] w-full h-full p-0">
          <DialogTitle className="sr-only">Roadmap Fullscreen View</DialogTitle>
          
          {/* 全屏工具栏 */}
          <div className="absolute top-4 right-4 z-50">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(false)}
              className="gap-2"
            >
              <Minimize2 className="w-4 h-4" />
              Exit Fullscreen
            </Button>
          </div>
          
          {/* 全屏内容 */}
          <div className="h-full w-full overflow-auto">
            <div className="p-8">
              <TreeViewContent
                nodes={filteredNodes}
                connections={filteredConnections}
                totalWidth={totalWidth}
                totalHeight={totalHeight}
                selectedNode={selectedNode}
                onNodeClick={handleNodeClick}
                onToggleExpand={handleToggleExpand}
                isEditing={isEditing}
                taskId={taskId}
              />
            </div>
          </div>
          
          {/* 全屏模式下的节点详情弹出层 */}
          <NodeDetailPopover
            node={selectedNode}
            isOpen={isPopoverOpen}
            onClose={handleClosePopover}
            anchorPosition={selectedNode?.position ? {
              x: selectedNode.position.x + 32, // 补偿 padding
              y: selectedNode.position.y + 32,
            } : undefined}
            roadmapId={roadmapId}
            userPreferences={userPreferences}
            onRetrySuccess={onRetrySuccess}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

