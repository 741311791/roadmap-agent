/**
 * Waitlist 管理页面
 * 
 * 超级管理员专用页面，用于管理候补名单并批量发送邀请邮件
 * 
 * 功能：
 * - 查看 Waitlist 列表（All / Pending / Invited 过滤）
 * - 批量选择用户
 * - 配置密码有效期
 * - 批量发送邀请邮件
 * - 显示凭证信息（已发送的）
 */
'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/lib/store/auth-store';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { Mail, Send, AlertCircle, CheckCircle2, Copy, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

// ============================================================
// 类型定义
// ============================================================

interface WaitlistInviteItem {
  email: string;
  source: string;
  invited: boolean;
  invited_at: string | null;
  created_at: string;
  username: string | null;
  password: string | null;
  expires_at: string | null;
  sent_content: {
    username: string;
    expires_at: string;
    sent_at: string;
    sent_by: string;
  } | null;
}

interface WaitlistInviteListResponse {
  items: WaitlistInviteItem[];
  total: number;
  pending: number;
  invited: number;
}

type FilterStatus = 'all' | 'pending' | 'invited';

// ============================================================
// 主组件
// ============================================================

export default function WaitlistManagementPage() {
  const { user } = useAuthStore();
  
  // 状态管理
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [data, setData] = useState<WaitlistInviteListResponse | null>(null);
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set());
  const [validityDays, setValidityDays] = useState(30);
  const [passwordVisibility, setPasswordVisibility] = useState<Record<string, boolean>>({});

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.get<WaitlistInviteListResponse>(
        `/admin/waitlist-invites?status=${filterStatus}&limit=100&offset=0`
      );
      setData(response.data);
      setSelectedEmails(new Set()); // 重置选中项
    } catch (error) {
      console.error('Failed to load waitlist:', error);
      toast.error('Failed to load waitlist');
    } finally {
      setIsLoading(false);
    }
  };

  // 切换过滤器时重新加载
  useEffect(() => {
    loadData();
  }, [filterStatus]);

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (!data) return;
    
    const pendingEmails = data.items
      .filter(item => !item.invited)
      .map(item => item.email);
    
    if (selectedEmails.size === pendingEmails.length) {
      setSelectedEmails(new Set());
    } else {
      setSelectedEmails(new Set(pendingEmails));
    }
  };

  // 切换单个选择
  const toggleSelect = (email: string) => {
    const newSelected = new Set(selectedEmails);
    if (newSelected.has(email)) {
      newSelected.delete(email);
    } else {
      newSelected.add(email);
    }
    setSelectedEmails(newSelected);
  };

  // 批量发送邀请
  const handleBatchSend = async () => {
    if (selectedEmails.size === 0) {
      toast.error('Please select at least one email');
      return;
    }

    try {
      setIsSending(true);
      const response = await apiClient.post<{
        success: number;
        failed: number;
        errors: Array<{ email: string; error: string }>;
      }>('/admin/waitlist-invites/batch-send', {
        emails: Array.from(selectedEmails),
        password_validity_days: validityDays,
      });

      const { success, failed, errors } = response.data;

      if (failed === 0) {
        toast.success(`Successfully sent ${success} invitation${success > 1 ? 's' : ''}`);
      } else {
        toast.warning(
          `Sent ${success} invitation${success > 1 ? 's' : ''}, ${failed} failed`,
          {
            description: errors.map(e => `${e.email}: ${e.error}`).join('\n'),
            duration: 8000,
          }
        );
      }

      // 重新加载数据
      await loadData();
    } catch (error) {
      console.error('Failed to send invitations:', error);
      toast.error('Failed to send invitations');
    } finally {
      setIsSending(false);
    }
  };

  // 复制到剪贴板
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  // 切换密码可见性
  const togglePasswordVisibility = (email: string) => {
    setPasswordVisibility(prev => ({
      ...prev,
      [email]: !prev[email],
    }));
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    try {
      return format(new Date(dateStr), 'MMM dd, yyyy HH:mm');
    } catch {
      return dateStr;
    }
  };

  if (!user) {
    return null;
  }

  const pendingCount = data?.items.filter(item => !item.invited).length || 0;
  const allSelected = pendingCount > 0 && selectedEmails.size === pendingCount;

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Mail className="w-8 h-8 text-sage-600" />
            <h1 className="text-4xl font-serif font-semibold text-foreground">
              Waitlist Management
            </h1>
          </div>
          <p className="text-muted-foreground">
            Send beta invitations to waitlist users
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => setFilterStatus('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'all'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            All
            {data && (
              <Badge variant="outline" className="ml-2 bg-background">
                {data.total}
              </Badge>
            )}
          </button>
          <button
            onClick={() => setFilterStatus('pending')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'pending'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            Pending
            {data && (
              <Badge variant="outline" className="ml-2 bg-background">
                {data.pending}
              </Badge>
            )}
          </button>
          <button
            onClick={() => setFilterStatus('invited')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterStatus === 'invited'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            Invited
            {data && (
              <Badge variant="outline" className="ml-2 bg-background">
                {data.invited}
              </Badge>
            )}
          </button>
        </div>

        {/* Batch Action Bar */}
        <div className="bg-card border border-border rounded-lg p-4 mb-6 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={allSelected}
              onCheckedChange={toggleSelectAll}
              disabled={pendingCount === 0}
            />
            <span className="text-sm text-foreground">
              Select All ({pendingCount} pending)
            </span>
          </div>

          {selectedEmails.size > 0 && (
            <>
              <div className="h-6 w-px bg-border" />
              <span className="text-sm font-medium text-sage-700">
                {selectedEmails.size} user{selectedEmails.size > 1 ? 's' : ''} selected
              </span>
            </>
          )}

          <div className="flex items-center gap-2 ml-auto">
            <label className="text-sm text-muted-foreground">Validity Days:</label>
            <Input
              type="number"
              value={validityDays}
              onChange={(e) => setValidityDays(Number(e.target.value))}
              className="w-20"
              min={1}
              max={365}
            />
          </div>

          <Button
            onClick={handleBatchSend}
            disabled={selectedEmails.size === 0 || isSending}
            className="gap-2"
          >
            <Send className="w-4 h-4" />
            {isSending ? 'Sending...' : 'Send Invitations'}
          </Button>
        </div>

        {/* Table */}
        {isLoading ? (
          <TableSkeleton rows={5} columns={7} />
        ) : !data || data.items.length === 0 ? (
          <div className="bg-card border border-border rounded-lg p-12 text-center">
            <Mail className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium text-foreground mb-2">
              No waitlist users found
            </h3>
            <p className="text-sm text-muted-foreground">
              {filterStatus === 'all'
                ? 'The waitlist is currently empty'
                : filterStatus === 'pending'
                ? 'No pending invitations'
                : 'No invitations sent yet'}
            </p>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12"></TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Credentials</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((item) => {
                  const isSelected = selectedEmails.has(item.email);
                  const showPassword = passwordVisibility[item.email];

                  return (
                    <TableRow key={item.email}>
                      <TableCell>
                        {!item.invited && (
                          <Checkbox
                            checked={isSelected}
                            onCheckedChange={() => toggleSelect(item.email)}
                          />
                        )}
                      </TableCell>
                      <TableCell className="font-medium">{item.email}</TableCell>
                      <TableCell className="text-muted-foreground capitalize">
                        {item.source.replace('_', ' ')}
                      </TableCell>
                      <TableCell>
                        {item.invited ? (
                          <Badge variant="sage" className="gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            Invited
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Pending
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.invited && item.username && item.password ? (
                          <div className="space-y-1 text-xs">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">User:</span>
                              <code className="bg-muted px-2 py-0.5 rounded">
                                {item.username}
                              </code>
                              <button
                                onClick={() => copyToClipboard(item.username!, 'Username')}
                                className="text-sage-600 hover:text-sage-700"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">Pass:</span>
                              <code className="bg-muted px-2 py-0.5 rounded font-mono">
                                {showPassword ? item.password : '••••••••'}
                              </code>
                              <button
                                onClick={() => togglePasswordVisibility(item.email)}
                                className="text-sage-600 hover:text-sage-700"
                              >
                                {showPassword ? (
                                  <EyeOff className="w-3 h-3" />
                                ) : (
                                  <Eye className="w-3 h-3" />
                                )}
                              </button>
                              <button
                                onClick={() => copyToClipboard(item.password!, 'Password')}
                                className="text-sage-600 hover:text-sage-700"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            </div>
                            {item.expires_at && (
                              <div className="text-muted-foreground">
                                Expires: {formatDate(item.expires_at)}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-muted-foreground text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDate(item.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        {!item.invited && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              setSelectedEmails(new Set([item.email]));
                              await handleBatchSend();
                            }}
                            disabled={isSending}
                            className="gap-1"
                          >
                            <Send className="w-3 h-3" />
                            Send
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

