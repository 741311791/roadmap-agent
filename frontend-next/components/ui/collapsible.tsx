/**
 * Collapsible 组件
 * 
 * 基于 Radix UI Collapsible 的可折叠容器组件
 */
'use client';

import * as React from 'react';
import * as CollapsiblePrimitive from '@radix-ui/react-collapsible';

const Collapsible = CollapsiblePrimitive.Root;

const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger;

const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent;

export { Collapsible, CollapsibleTrigger, CollapsibleContent };

