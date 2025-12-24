'use client';

import React, { useEffect, useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { Stage, Module, Concept } from '@/types/generated/models';
import { CheckCircle2, Circle, ChevronRight, ChevronDown, ChevronLeft, Sparkles } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { UserMenu } from '@/components/user-menu';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/ui/button';

/**
 * KnowledgeRailProps - 知识导航栏组件属性
 */
interface KnowledgeRailProps {
  /** 路线图数据，包含阶段列表 */
  roadmap: {
    title?: string;
    stages: Stage[];
  } | null;
  /** 当前激活的概念 ID */
  activeConceptId: string | null;
  /** 选择概念的回调函数 */
  onSelectConcept: (id: string) => void;
  /** 自定义样式类名 */
  className?: string;
  /** 生成进度百分比 (0-100) */
  generationProgress?: number;
}

/**
 * KnowledgeRail - 沉浸式学习页面的左侧知识导航栏
 * 
 * 功能:
 * - 展示 Stage → Module → Concept 的层级结构
 * - 支持模块折叠/展开
 * - 高亮当前选中的概念
 * - 显示学习进度
 */
export function KnowledgeRail({ 
  roadmap, 
  activeConceptId, 
  onSelectConcept,
  className,
  generationProgress 
}: KnowledgeRailProps) {
  const [expandedModules, setExpandedModules] = React.useState<Set<string>>(new Set());

  // 计算包含活跃概念的模块ID列表
  const modulesWithActiveConcept = useMemo(() => {
    if (!roadmap || !activeConceptId) return new Set<string>();
    
    const moduleIds = new Set<string>();
    for (const stage of roadmap.stages) {
      for (const module of stage.modules) {
        if (module.concepts.some(c => c.concept_id === activeConceptId)) {
          moduleIds.add(module.module_id);
        }
      }
    }
    return moduleIds;
  }, [roadmap, activeConceptId]);

  // 当活跃概念变化时，自动展开包含该概念的模块
  useEffect(() => {
    if (modulesWithActiveConcept.size > 0) {
      setExpandedModules(prev => {
        const next = new Set(prev);
        modulesWithActiveConcept.forEach(id => next.add(id));
        return next;
      });
    }
  }, [modulesWithActiveConcept]);

  const toggleModule = (moduleId: string) => {
    setExpandedModules(prev => {
      const next = new Set(prev);
      if (next.has(moduleId)) {
        next.delete(moduleId);
      } else {
        next.add(moduleId);
      }
      return next;
    });
  };

  if (!roadmap) {
    return (
      <div className={cn("h-full flex items-center justify-center text-muted-foreground", className)}>
        <span className="font-serif">Loading...</span>
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={300}>
      <div className={cn(
        "h-full flex flex-col",
        "bg-card/80 border-r border-border",
        className
      )}>
        {/* Brand Header - 品牌区域 */}
        <div className="p-4 border-b border-border space-y-3">
          {/* Back to Dashboard Breadcrumb */}
          <Link href="/home">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 px-2 -ml-2 -mt-1 text-muted-foreground hover:text-foreground hover:bg-sage-50 gap-1 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Dashboard</span>
            </Button>
          </Link>

          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="relative w-10 h-10 shrink-0">
              <Image
                src="/logo/svg_noword.svg"
                alt="Logo"
                fill
                className="object-contain"
              />
            </div>
            {/* Product Name */}
            <div className="flex-1 min-w-0">
              <h1 className="text-sm font-serif font-semibold text-foreground">
                Fast Learning
              </h1>
              <p className="text-xs text-muted-foreground truncate">
                Your Learning Path
              </p>
            </div>
          </div>

          {/* Roadmap Title */}
          <div className="space-y-2">
            <h2 className="text-sm font-serif font-medium text-foreground leading-tight line-clamp-2">
              {roadmap.title || 'Untitled Roadmap'}
            </h2>
            
            {/* Progress Badge with Tooltip */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">
                Progress
              </span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge 
                    variant="sage"
                    className="text-xs font-medium flex items-center gap-1 cursor-help"
                  >
                    <Sparkles className="w-3 h-3" />
                    {Math.round(generationProgress || 0)}%
                  </Badge>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">
                  <p>Overall completion: {Math.round(generationProgress || 0)}%</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>

        {/* Concept Navigation - 概念导航 */}
        <ScrollArea className="flex-1 px-2 py-4">
          <div className="space-y-6 relative">
            {/* Vertical Timeline Line - 对齐圆圈中心 */}
            <div 
              className="absolute left-[20px] top-2 bottom-2 w-px bg-border"
            />

            {roadmap.stages
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((stage) => (
                <StageItem
                  key={stage.stage_id}
                  stage={stage}
                  expandedModules={expandedModules}
                  activeConceptId={activeConceptId}
                  onToggleModule={toggleModule}
                  onSelectConcept={onSelectConcept}
                />
              ))}
          </div>
        </ScrollArea>

        {/* User Menu Footer - 底部用户菜单（使用统一组件） */}
        <div className="p-2 border-t border-border bg-background/50">
          <UserMenu compact />
        </div>
      </div>
    </TooltipProvider>
  );
}

/**
 * StageItem - 阶段项组件
 */
interface StageItemProps {
  stage: Stage;
  expandedModules: Set<string>;
  activeConceptId: string | null;
  onToggleModule: (moduleId: string) => void;
  onSelectConcept: (conceptId: string) => void;
}

function StageItem({ 
  stage, 
  expandedModules, 
  activeConceptId, 
  onToggleModule, 
  onSelectConcept 
}: StageItemProps) {
  return (
    <div className="relative z-10">
      <div className="flex items-center gap-3 mb-2 px-2">
        {/* Stage Number Circle */}
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
          "bg-sage-100 border border-sage-200",
          "transition-colors duration-200"
        )}>
          <span className="text-xs font-mono text-sage-700">{stage.order}</span>
        </div>
        {/* Stage Name */}
        <h3 className="text-sm font-serif font-medium text-foreground">{stage.name}</h3>
      </div>

      {/* 移除 border-l，避免和全局竖线重复 */}
      <div className="ml-4 pl-4 space-y-2">
        {stage.modules.map((module) => (
          <ModuleItem
            key={module.module_id}
            module={module}
            isExpanded={expandedModules.has(module.module_id)}
            activeConceptId={activeConceptId}
            onToggle={() => onToggleModule(module.module_id)}
            onSelectConcept={onSelectConcept}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * ModuleItem - 模块项组件
 */
interface ModuleItemProps {
  module: Module;
  isExpanded: boolean;
  activeConceptId: string | null;
  onToggle: () => void;
  onSelectConcept: (conceptId: string) => void;
}

function ModuleItem({ 
  module, 
  isExpanded, 
  activeConceptId, 
  onToggle, 
  onSelectConcept 
}: ModuleItemProps) {
  const hasActiveConcept = module.concepts.some(c => c.concept_id === activeConceptId);

  return (
    <div className="group">
      <button
        onClick={onToggle}
        className={cn(
          "flex items-center gap-2 w-full text-left p-2 rounded-md transition-colors",
          "hover:bg-sage-50"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="w-3 h-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
        )}
        <span className={cn(
          "text-xs font-medium truncate transition-colors",
          hasActiveConcept 
            ? "text-sage-700" 
            : "text-muted-foreground group-hover:text-foreground"
        )}>
          {module.name}
        </span>
      </button>

      {isExpanded && (
        <div className="ml-5 mt-1 space-y-0.5 border-l border-border pl-2">
          {module.concepts.map((concept) => (
            <ConceptItem
              key={concept.concept_id}
              concept={concept}
              isActive={concept.concept_id === activeConceptId}
              onSelect={() => onSelectConcept(concept.concept_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * ConceptItem - 概念项组件
 */
interface ConceptItemProps {
  concept: Concept;
  isActive: boolean;
  onSelect: () => void;
}

function ConceptItem({ concept, isActive, onSelect }: ConceptItemProps) {
  const { conceptProgressMap } = useRoadmapStore();
  const isCompleted = conceptProgressMap[concept.concept_id] || false;

  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full text-left px-3 py-2 rounded-md text-xs transition-all flex items-center gap-2 relative overflow-hidden",
        isActive
          ? "bg-sage-100 text-sage-800 border border-sage-200"
          : "text-muted-foreground hover:text-foreground hover:bg-sage-50/50"
      )}
    >
      {/* Active Indicator Bar */}
      {isActive && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-sage-500" />
      )}

      {/* Status Icon */}
      {isCompleted ? (
        <CheckCircle2 className={cn(
          "w-3 h-3 shrink-0",
          isActive ? "text-sage-600" : "text-sage-400"
        )} />
      ) : (
        <Circle className="w-3 h-3 shrink-0 text-muted-foreground/50" />
      )}
      
      {/* Concept Name */}
      <span className="truncate">{concept.name}</span>
    </button>
  );
}
