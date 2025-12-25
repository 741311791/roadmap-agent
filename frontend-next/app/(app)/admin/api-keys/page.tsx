'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Key, Plus, Trash2, Loader2, RefreshCw, Upload } from 'lucide-react';
import {
  getTavilyAPIKeys,
  addTavilyAPIKey,
  batchAddTavilyAPIKeys,
  deleteTavilyAPIKey,
  type TavilyAPIKeyInfo,
  type AddTavilyAPIKeyRequest,
} from '@/lib/api/tavily-keys';
import { useAuthStore } from '@/lib/store/auth-store';
import { cn } from '@/lib/utils';

export default function APIKeysManagementPage() {
  const { isAdmin } = useAuthStore();
  
  // 状态管理
  const [keys, setKeys] = useState<TavilyAPIKeyInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 添加单个 Key 表单
  const [newKey, setNewKey] = useState('');
  const [newPlanLimit, setNewPlanLimit] = useState('1000');
  const [isAdding, setIsAdding] = useState(false);
  
  // 批量添加
  const [batchInput, setBatchInput] = useState('');
  const [isBatchAdding, setIsBatchAdding] = useState(false);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [batchResult, setBatchResult] = useState<{
    success: number;
    failed: number;
    errors: Array<{ api_key: string; error: string }>;
  } | null>(null);
  
  // 删除确认
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 权限检查
  useEffect(() => {
    if (!isAdmin()) {
      setError('You do not have permission to access this page');
      setIsLoading(false);
    } else {
      loadKeys();
    }
  }, [isAdmin]);

  /**
   * 加载所有 API Keys
   */
  const loadKeys = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await getTavilyAPIKeys();
      setKeys(response.keys);
    } catch (err) {
      console.error('Failed to load API keys:', err);
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 添加单个 API Key
   */
  const handleAddKey = async () => {
    if (!newKey.trim()) {
      return;
    }

    try {
      setIsAdding(true);
      await addTavilyAPIKey({
        api_key: newKey.trim(),
        plan_limit: parseInt(newPlanLimit) || 1000,
      });
      
      // 重新加载列表
      await loadKeys();
      
      // 清空表单
      setNewKey('');
      setNewPlanLimit('1000');
    } catch (err) {
      console.error('Failed to add API key:', err);
      alert(err instanceof Error ? err.message : 'Failed to add API key');
    } finally {
      setIsAdding(false);
    }
  };

  /**
   * 批量添加 API Keys
   * 
   * 支持格式：
   * 1. 每行一个 Key（使用默认配额1000）
   * 2. 每行格式：key,limit
   */
  const handleBatchAdd = async () => {
    const lines = batchInput.trim().split('\n').filter(line => line.trim());
    
    if (lines.length === 0) {
      alert('Please enter at least one API key');
      return;
    }

    const keysToAdd: AddTavilyAPIKeyRequest[] = [];
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue;
      
      // 检查是否包含逗号（key,limit格式）
      if (trimmedLine.includes(',')) {
        const [key, limitStr] = trimmedLine.split(',').map(s => s.trim());
        const limit = parseInt(limitStr) || 1000;
        keysToAdd.push({ api_key: key, plan_limit: limit });
      } else {
        // 只有 Key，使用默认配额
        keysToAdd.push({ api_key: trimmedLine, plan_limit: 1000 });
      }
    }

    try {
      setIsBatchAdding(true);
      const result = await batchAddTavilyAPIKeys({ keys: keysToAdd });
      
      // 显示结果
      setBatchResult(result);
      
      // 重新加载列表
      await loadKeys();
      
      // 如果全部成功，清空输入框
      if (result.failed === 0) {
        setBatchInput('');
        setShowBatchDialog(false);
      }
    } catch (err) {
      console.error('Failed to batch add API keys:', err);
      alert(err instanceof Error ? err.message : 'Failed to batch add API keys');
    } finally {
      setIsBatchAdding(false);
    }
  };

  /**
   * 删除 API Key
   */
  const handleDeleteKey = async (apiKey: string) => {
    try {
      setIsDeleting(true);
      await deleteTavilyAPIKey(apiKey);
      
      // 重新加载列表
      await loadKeys();
      
      // 关闭确认对话框
      setKeyToDelete(null);
    } catch (err) {
      console.error('Failed to delete API key:', err);
      alert(err instanceof Error ? err.message : 'Failed to delete API key');
    } finally {
      setIsDeleting(false);
    }
  };

  /**
   * 格式化日期时间
   */
  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /**
   * 计算配额使用百分比
   */
  const getQuotaPercentage = (remaining: number, total: number) => {
    return total > 0 ? Math.round((remaining / total) * 100) : 0;
  };

  /**
   * 获取配额状态颜色
   */
  const getQuotaColor = (percentage: number) => {
    if (percentage >= 50) return 'text-green-600';
    if (percentage >= 20) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (error && !isAdmin()) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-6 text-center">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-serif font-bold text-charcoal flex items-center gap-3">
              <Key className="w-8 h-8 text-sage-600" />
              API Keys Management
            </h1>
            <p className="text-muted-foreground">
              Manage Tavily API Keys for web search functionality
            </p>
          </div>
          
          <Button
            onClick={loadKeys}
            disabled={isLoading}
            variant="outline"
            className="gap-2"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            Refresh
          </Button>
        </div>

        {/* Statistics */}
        {!isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="text-sm text-muted-foreground">Total Keys</div>
                <div className="text-3xl font-bold text-charcoal mt-1">{keys.length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="text-sm text-muted-foreground">Total Quota</div>
                <div className="text-3xl font-bold text-charcoal mt-1">
                  {keys.reduce((sum, key) => sum + key.plan_limit, 0).toLocaleString()}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <div className="text-sm text-muted-foreground">Remaining Quota</div>
                <div className="text-3xl font-bold text-sage-600 mt-1">
                  {keys.reduce((sum, key) => sum + key.remaining_quota, 0).toLocaleString()}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Add Single Key */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Add New API Key
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 space-y-2">
                <Label>API Key</Label>
                <Input
                  type="text"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="tvly-xxxxxxxxxxxxxxxxxxxxx"
                  disabled={isAdding}
                />
              </div>
              <div className="space-y-2">
                <Label>Plan Limit</Label>
                <Input
                  type="number"
                  value={newPlanLimit}
                  onChange={(e) => setNewPlanLimit(e.target.value)}
                  placeholder="1000"
                  disabled={isAdding}
                />
              </div>
            </div>
            <Button
              onClick={handleAddKey}
              disabled={isAdding || !newKey.trim()}
              className="gap-2"
            >
              {isAdding ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Add Key
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Batch Add */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Batch Add API Keys
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>
                API Keys (one per line, format: key or key,limit)
              </Label>
              <Textarea
                value={batchInput}
                onChange={(e) => setBatchInput(e.target.value)}
                placeholder={'tvly-xxxxxxxxxxxxxxxxxxxxx\ntvly-yyyyyyyyyyyyyyyyyyyyy,2000\ntvly-zzzzzzzzzzzzzzzzzzzzz'}
                rows={6}
                disabled={isBatchAdding}
                className="font-mono text-sm"
              />
            </div>
            
            {batchResult && (
              <div className="p-4 rounded-lg bg-muted space-y-2">
                <div className="font-medium">Batch Add Result:</div>
                <div className="text-sm space-y-1">
                  <div className="text-green-600">✓ Success: {batchResult.success}</div>
                  <div className="text-red-600">✗ Failed: {batchResult.failed}</div>
                  {batchResult.errors.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <div className="font-medium text-destructive">Errors:</div>
                      {batchResult.errors.map((err, idx) => (
                        <div key={idx} className="text-xs text-muted-foreground">
                          {err.api_key}: {err.error}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <Button
              onClick={handleBatchAdd}
              disabled={isBatchAdding || !batchInput.trim()}
              variant="sage"
              className="gap-2"
            >
              {isBatchAdding ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Batch Add
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* API Keys Table */}
        <Card>
          <CardHeader>
            <CardTitle>Current API Keys</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-sage-600" />
              </div>
            ) : keys.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No API keys found. Add your first key above.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>API Key</TableHead>
                      <TableHead>Plan Limit</TableHead>
                      <TableHead>Remaining</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Created At</TableHead>
                      <TableHead>Updated At</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {keys.map((key) => {
                      const percentage = getQuotaPercentage(
                        key.remaining_quota,
                        key.plan_limit
                      );
                      
                      return (
                        <TableRow key={key.api_key}>
                          <TableCell className="font-mono text-sm">
                            {key.api_key}
                          </TableCell>
                          <TableCell>{key.plan_limit.toLocaleString()}</TableCell>
                          <TableCell>
                            <span className={cn('font-medium', getQuotaColor(percentage))}>
                              {key.remaining_quota.toLocaleString()}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden max-w-[100px]">
                                <div
                                  className={cn(
                                    'h-full transition-all',
                                    percentage >= 50 ? 'bg-green-500' :
                                    percentage >= 20 ? 'bg-yellow-500' :
                                    'bg-red-500'
                                  )}
                                  style={{ width: `${percentage}%` }}
                                />
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {percentage}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDateTime(key.created_at)}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDateTime(key.updated_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setKeyToDelete(key.api_key)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!keyToDelete} onOpenChange={() => setKeyToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete API Key</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this API key? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => keyToDelete && handleDeleteKey(keyToDelete)}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

