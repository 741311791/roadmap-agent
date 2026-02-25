/**
 * ResponsiveTable - 响应式表格组件
 * 
 * 移动端：卡片列表
 * 桌面端：标准表格
 * 
 * @example
 * <ResponsiveTable
 *   data={tasks}
 *   columns={columns}
 *   renderMobileCard={(item) => <TaskCard task={item} />}
 * />
 */

'use client';

import * as React from 'react';
import { useIsMobile } from '@/lib/hooks';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface Column<T> {
  /** 列标题 */
  header: string;
  /** 数据访问器（字段名或渲染函数）*/
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  /** 列宽度类名（仅桌面端）*/
  className?: string;
}

interface ResponsiveTableProps<T> {
  /** 数据数组 */
  data: T[];
  /** 列定义（桌面端表格使用）*/
  columns: Column<T>[];
  /** 移动端卡片渲染函数 */
  renderMobileCard: (item: T, index: number) => React.ReactNode;
  /** 获取行唯一 key */
  getRowKey: (item: T, index: number) => string | number;
  /** 容器类名 */
  className?: string;
  /** 空状态组件 */
  emptyState?: React.ReactNode;
}

export function ResponsiveTable<T>({
  data,
  columns,
  renderMobileCard,
  getRowKey,
  className,
  emptyState,
}: ResponsiveTableProps<T>) {
  const isMobile = useIsMobile();

  // 空状态
  if (data.length === 0 && emptyState) {
    return <div className={className}>{emptyState}</div>;
  }

  // 移动端：卡片列表
  if (isMobile) {
    return (
      <div className={cn('space-y-4', className)}>
        {data.map((item, index) => (
          <React.Fragment key={getRowKey(item, index)}>
            {renderMobileCard(item, index)}
          </React.Fragment>
        ))}
      </div>
    );
  }

  // 桌面端：标准表格
  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column, index) => (
              <TableHead key={index} className={column.className}>
                {column.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((item, index) => (
            <TableRow key={getRowKey(item, index)}>
              {columns.map((column, colIndex) => (
                <TableCell key={colIndex} className={column.className}>
                  {column.cell
                    ? column.cell(item)
                    : column.accessorKey
                    ? String(item[column.accessorKey])
                    : null}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * 移动端卡片包装器（提供统一样式）
 */
interface MobileCardWrapperProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function MobileCardWrapper({
  children,
  className,
  onClick,
}: MobileCardWrapperProps) {
  return (
    <Card
      className={cn(
        'p-4 space-y-3',
        onClick && 'cursor-pointer hover:bg-accent/50 transition-colors',
        className
      )}
      onClick={onClick}
    >
      {children}
    </Card>
  );
}

/**
 * 移动端卡片行（标签 + 值）
 */
interface MobileCardRowProps {
  label: string;
  value: React.ReactNode;
  className?: string;
}

export function MobileCardRow({ label, value, className }: MobileCardRowProps) {
  return (
    <div className={cn('flex items-center justify-between gap-2', className)}>
      <span className="text-sm text-muted-foreground font-medium">{label}</span>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}
