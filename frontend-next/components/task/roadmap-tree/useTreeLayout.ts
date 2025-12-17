/**
 * useTreeLayout - 树布局计算 Hook
 * 
 * 递归计算树节点的位置，生成 SVG 连接线数据
 */

import { useMemo } from 'react';
import type { Stage, Module, Concept } from '@/types/generated/models';
import {
  TreeNodeData,
  ExpansionState,
  ConnectionLine,
  NodePosition,
  TreeNodeType,
  TREE_LAYOUT_CONFIG,
  getConceptNodeStatus,
  getModuleNodeStatus,
  getStageNodeStatus,
} from './types';

/**
 * 计算节点宽度（基于名称长度）
 * 改进版：更准确地计算中英文混合文本宽度
 */
function calculateNodeWidth(name: string, type: TreeNodeType, hasChildren: boolean, hasStatus: boolean): number {
  const config = TREE_LAYOUT_CONFIG;
  const minWidth = config.minNodeWidth[type];
  const charWidth = config.charWidth[type];
  const paddingWidth = config.paddingWidth[type];
  
  // 计算图标占用的宽度
  let iconWidth: number = config.iconWidth.none;
  if (hasChildren && hasStatus) {
    iconWidth = config.iconWidth.withBoth;
  } else if (hasChildren) {
    iconWidth = config.iconWidth.withExpand;
  } else if (hasStatus) {
    iconWidth = config.iconWidth.withStatus;
  }
  
  // 计算文本宽度 - 中文字符按1.5倍计算，英文按1倍
  let textWidth = 0;
  for (let i = 0; i < name.length; i++) {
    const char = name[i];
    // 判断是否为中文字符（包括中文标点）
    if (/[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/.test(char)) {
      textWidth += charWidth * 1.6; // 中文字符更宽
    } else {
      textWidth += charWidth;
    }
  }
  
  // 总宽度 = padding + 图标 + 文本，不再限制最大宽度
  const totalWidth = paddingWidth + iconWidth + textWidth;
  
  // 只限制最小宽度，让节点完全自适应内容
  return Math.max(minWidth, totalWidth);
}

interface UseTreeLayoutOptions {
  /** 路线图阶段数据 */
  stages: Stage[];
  /** 展开状态 */
  expansionState: ExpansionState;
  /** 修改过的节点 ID */
  modifiedNodeIds?: string[];
  /** 加载中的 Concept ID */
  loadingConceptIds?: string[];
  /** 失败的 Concept ID */
  failedConceptIds?: string[];
  /** 部分失败的 Concept ID */
  partialFailedConceptIds?: string[];
}

interface UseTreeLayoutResult {
  /** 带位置信息的树节点数据 */
  nodes: TreeNodeData[];
  /** SVG 连接线数据 */
  connections: ConnectionLine[];
  /** 画布总宽度 */
  totalWidth: number;
  /** 画布总高度 */
  totalHeight: number;
}

/**
 * 计算树布局
 */
export function useTreeLayout({
  stages,
  expansionState,
  modifiedNodeIds = [],
  loadingConceptIds = [],
  failedConceptIds = [],
  partialFailedConceptIds = [],
  showStartNode = false,
}: UseTreeLayoutOptions & { showStartNode?: boolean }): UseTreeLayoutResult {
  return useMemo(() => {
    const config = TREE_LAYOUT_CONFIG;
    const nodes: TreeNodeData[] = [];
    const connections: ConnectionLine[] = [];
    
    // 起始位置
    let currentY = 20;
    let startX = 20;
    
    // 如果显示起始节点，添加起始节点
    let startNode: TreeNodeData | undefined;
    if (showStartNode) {
      const startNodeWidth = calculateNodeWidth('Intent Analysis', 'start', true, true);
      startNode = {
        id: 'start-node',
        type: 'start',
        name: 'Intent Analysis',
        description: 'Learning goal analysis and roadmap planning',
        status: 'completed',
        position: {
          x: startX,
          y: currentY + 60,
          width: startNodeWidth,
          height: config.nodeHeight,
        },
      };
      nodes.push(startNode);
      startX = startX + startNodeWidth + config.horizontalGap;
    }
    
    /**
     * 递归计算子树高度（用于垂直居中）
     */
    function calculateSubtreeHeight(
      node: TreeNodeData,
      depth: number,
    ): number {
      if (!node.children || node.children.length === 0 || !node.isExpanded) {
        return config.nodeHeight;
      }
      
      const childrenHeight = node.children.reduce((total, child, index) => {
        const childHeight = calculateSubtreeHeight(child, depth + 1);
        return total + childHeight + (index > 0 ? config.verticalGap : 0);
      }, 0);
      
      return Math.max(config.nodeHeight, childrenHeight);
    }
    
    /**
     * 将 Concept 转换为 TreeNodeData
     */
    function conceptToNode(concept: Concept): TreeNodeData {
      const status = getConceptNodeStatus(
        concept,
        loadingConceptIds,
        failedConceptIds,
        partialFailedConceptIds,
        modifiedNodeIds,
      );
      
      return {
        id: concept.concept_id,
        type: 'concept',
        name: concept.name,
        description: concept.description,
        status,
        estimatedHours: concept.estimated_hours,
        isModified: modifiedNodeIds.includes(concept.concept_id),
        originalData: concept,
      };
    }
    
    /**
     * 将 Module 转换为 TreeNodeData
     */
    function moduleToNode(module: Module): TreeNodeData {
      const conceptNodes = module.concepts.map(conceptToNode);
      const childStatuses = conceptNodes.map(n => n.status);
      const status = getModuleNodeStatus(childStatuses);
      const isExpanded = expansionState[module.module_id] ?? false; // 默认收起 Concept
      
      return {
        id: module.module_id,
        type: 'module',
        name: module.name,
        description: module.description,
        status,
        isExpanded,
        isModified: modifiedNodeIds.includes(module.module_id),
        children: conceptNodes,
        originalData: module,
      };
    }
    
    /**
     * 将 Stage 转换为 TreeNodeData
     */
    function stageToNode(stage: Stage): TreeNodeData {
      const moduleNodes = stage.modules.map(moduleToNode);
      const childStatuses = moduleNodes.map(n => n.status);
      const status = getStageNodeStatus(childStatuses);
      const isExpanded = expansionState[stage.stage_id] ?? true; // 默认展开 Module
      
      return {
        id: stage.stage_id,
        type: 'stage',
        name: stage.name,
        description: stage.description,
        status,
        isExpanded,
        isModified: modifiedNodeIds.includes(stage.stage_id),
        children: moduleNodes,
        originalData: stage,
      };
    }
    
    /**
     * 递归计算节点位置
     */
    function layoutNode(
      node: TreeNodeData,
      x: number,
      startY: number,
      parentNode?: TreeNodeData,
    ): number {
      // 计算节点宽度（基于名称）
      const hasChildren = !!(node.children && node.children.length > 0);
      const hasStatus = node.status !== 'pending';
      const nodeWidth = calculateNodeWidth(node.name, node.type, hasChildren, hasStatus);
      const nodeHeight: number = config.nodeHeight;
      
      // 如果有子节点且展开，计算子树高度用于垂直居中
      let subtreeHeight = nodeHeight;
      if (node.children && node.children.length > 0 && node.isExpanded) {
        subtreeHeight = calculateSubtreeHeight(node, 0);
      }
      
      // 计算节点 Y 位置（在子树中垂直居中）
      const nodeY = startY + (subtreeHeight - nodeHeight) / 2;
      
      // 设置节点位置
      node.position = {
        x,
        y: nodeY,
        width: nodeWidth,
        height: nodeHeight,
      };
      
      // 添加到节点列表
      nodes.push(node);
      
      // 添加连接线（从父节点到当前节点）
      if (parentNode && parentNode.position) {
        connections.push({
          id: `${parentNode.id}-${node.id}`,
          fromNodeId: parentNode.id,
          toNodeId: node.id,
          fromPosition: {
            x: parentNode.position.x + parentNode.position.width,
            y: parentNode.position.y + parentNode.position.height / 2,
          },
          toPosition: {
            x: node.position.x,
            y: node.position.y + nodeHeight / 2,
          },
        });
      }
      
      // 如果有子节点且展开，递归布局
      if (node.children && node.children.length > 0 && node.isExpanded) {
        const childX = x + nodeWidth + config.horizontalGap;
        let childY = startY;
        
        node.children.forEach((child, index) => {
          const childSubtreeHeight = calculateSubtreeHeight(child, 0);
          layoutNode(child, childX, childY, node);
          childY += childSubtreeHeight + config.verticalGap;
        });
      }
      
      return subtreeHeight;
    }
    
    // 布局所有 Stage
    const stageNodes = stages.map(stageToNode);
    
    stageNodes.forEach((stageNode, index) => {
      const stageHeight = layoutNode(stageNode, startX, currentY, startNode);
      currentY += stageHeight + config.verticalGap * 2;
    });
    
    // 如果有起始节点，重新计算其垂直居中位置
    if (startNode && startNode.position) {
      // 计算所有Stage的总高度范围
      const stageNodesOnly = nodes.filter(n => n.type === 'stage');
      if (stageNodesOnly.length > 0) {
        const minY = Math.min(...stageNodesOnly.map(n => n.position!.y));
        const maxY = Math.max(...stageNodesOnly.map(n => n.position!.y + n.position!.height));
        const centerY = (minY + maxY) / 2;
        
        // 更新起始节点的Y位置，使其垂直居中
        startNode.position.y = centerY - config.nodeHeight / 2;
        
        // 更新所有从起始节点出发的连接线
        connections.forEach(conn => {
          if (conn.fromNodeId === 'start-node') {
            conn.fromPosition.y = startNode.position!.y + config.nodeHeight / 2;
          }
        });
      }
    }
    
    // 计算画布尺寸
    let maxX = 0;
    let maxY = 0;
    
    nodes.forEach(node => {
      if (node.position) {
        maxX = Math.max(maxX, node.position.x + node.position.width);
        maxY = Math.max(maxY, node.position.y + node.position.height);
      }
    });
    
    return {
      nodes,
      connections,
      totalWidth: maxX + 40, // 添加右侧边距
      totalHeight: maxY + 40, // 添加底部边距
    };
  }, [
    stages,
    expansionState,
    modifiedNodeIds,
    loadingConceptIds,
    failedConceptIds,
    partialFailedConceptIds,
    showStartNode, // 添加依赖
  ]);
}

/**
 * 生成默认展开状态
 * 默认：Stage 展开，Module 收起（只展开到 Module 级别）
 */
export function getDefaultExpansionState(stages: Stage[]): ExpansionState {
  const state: ExpansionState = {};
  
  stages.forEach(stage => {
    // Stage 默认展开
    state[stage.stage_id] = true;
    
    // Module 默认收起（不展开 Concept）
    stage.modules.forEach(module => {
      state[module.module_id] = false;
    });
  });
  
  return state;
}

