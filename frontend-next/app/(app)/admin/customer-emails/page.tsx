'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { format } from 'date-fns';
import { Megaphone, Mail, Search, Send } from 'lucide-react';
import { TableSkeleton } from '@/components/common/loading-skeleton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { apiClient } from '@/lib/api/client';
import { useAuthStore } from '@/lib/store/auth-store';
import {
  composeEmailHtml,
  DEFAULT_EMAIL_TEMPLATE_SHELL,
} from '@/lib/utils/customer-email-renderer';
import { toast } from 'sonner';

type StatusFilter = 'all' | 'active' | 'inactive';
type TemplateKey = 'custom' | 'product_update' | 'promotion';

interface CustomerEmailUserItem {
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
}

interface CustomerEmailUserListResponse {
  items: CustomerEmailUserItem[];
  total: number;
}

interface CustomerEmailTemplateItem {
  key: Exclude<TemplateKey, 'custom'>;
  name: string;
  description: string;
  subject: string;
  html_content: string;
  text_content: string | null;
}

interface CustomerEmailTemplateListResponse {
  items: CustomerEmailTemplateItem[];
}

interface CustomerEmailSendResponse {
  success: number;
  failed: number;
  errors: Array<{ email: string; error: string }>;
}

/**
 * 将日期字符串格式化为可读文本。
 *
 * Args:
 *   dateStr: 原始日期字符串
 *
 * Returns:
 *   格式化后的日期文本
 */
function formatDate(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'MMM dd, yyyy HH:mm');
  } catch {
    return dateStr;
  }
}

/**
 * 客户邮件管理页面。
 *
 * Returns:
 *   管理员客户邮件页面
 */
export default function CustomerEmailsManagementPage() {
  const { user } = useAuthStore();

  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [isSending, setIsSending] = useState(false);

  const [keyword, setKeyword] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active');
  const [includeSuperusers, setIncludeSuperusers] = useState(false);

  const [users, setUsers] = useState<CustomerEmailUserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set());

  const [templates, setTemplates] = useState<CustomerEmailTemplateItem[]>([]);
  const [templateKey, setTemplateKey] = useState<TemplateKey>('custom');
  const [subject, setSubject] = useState('');
  const [htmlContent, setHtmlContent] = useState(DEFAULT_EMAIL_TEMPLATE_SHELL);
  const [textContent, setTextContent] = useState('');

  /**
   * 加载模板列表。
   *
   * Returns:
   *   无返回值
   */
  const loadTemplates = useCallback(async (): Promise<void> => {
    try {
      setIsLoadingTemplates(true);
      const response = await apiClient.get<CustomerEmailTemplateListResponse>(
        '/admin/customer-emails/templates'
      );
      setTemplates(response.data.items);
    } catch (error) {
      console.error('Failed to load email templates:', error);
      toast.error('Failed to load email templates');
    } finally {
      setIsLoadingTemplates(false);
    }
  }, []);

  /**
   * 加载用户列表。
   *
   * Returns:
   *   无返回值
   */
  const loadUsers = useCallback(async (): Promise<void> => {
    try {
      setIsLoadingUsers(true);
      const params = new URLSearchParams({
        limit: '100',
        offset: '0',
        include_superusers: String(includeSuperusers),
      });

      if (searchKeyword.trim()) {
        params.set('keyword', searchKeyword.trim());
      }

      if (statusFilter !== 'all') {
        params.set('is_active', String(statusFilter === 'active'));
      }

      const response = await apiClient.get<CustomerEmailUserListResponse>(
        `/admin/customer-emails/users?${params.toString()}`
      );

      setUsers(response.data.items);
      setTotal(response.data.total);
      setSelectedEmails(new Set());
    } catch (error) {
      console.error('Failed to load users:', error);
      toast.error('Failed to load users');
    } finally {
      setIsLoadingUsers(false);
    }
  }, [includeSuperusers, searchKeyword, statusFilter]);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  /**
   * 处理模板切换，并将模板内容带入编辑器。
   *
   * Args:
   *   nextTemplateKey: 新模板标识
   *
   * Returns:
   *   无返回值
   */
  const handleTemplateChange = (nextTemplateKey: string): void => {
    const normalizedKey = nextTemplateKey as TemplateKey;
    setTemplateKey(normalizedKey);

    if (normalizedKey === 'custom') {
      if (!htmlContent.trim()) {
        setHtmlContent(DEFAULT_EMAIL_TEMPLATE_SHELL);
      }
      return;
    }

    const template = templates.find((item) => item.key === normalizedKey);
    if (!template) {
      return;
    }

    setSubject(template.subject);
    setHtmlContent(template.html_content);
    setTextContent(template.text_content ?? '');
  };

  /**
   * 处理单个收件人勾选。
   *
   * Args:
   *   email: 用户邮箱
   *
   * Returns:
   *   无返回值
   */
  const toggleSelect = (email: string): void => {
    const nextSelectedEmails = new Set(selectedEmails);

    if (nextSelectedEmails.has(email)) {
      nextSelectedEmails.delete(email);
    } else {
      nextSelectedEmails.add(email);
    }

    setSelectedEmails(nextSelectedEmails);
  };

  /**
   * 处理当前列表全选或取消全选。
   *
   * Returns:
   *   无返回值
   */
  const toggleSelectAll = (): void => {
    const currentEmails = users.map((item) => item.email);

    if (selectedEmails.size === currentEmails.length) {
      setSelectedEmails(new Set());
      return;
    }

    setSelectedEmails(new Set(currentEmails));
  };

  /**
   * 执行用户搜索。
   *
   * Returns:
   *   无返回值
   */
  const handleSearch = async (): Promise<void> => {
    const nextSearchKeyword = keyword.trim();
    setSearchKeyword(nextSearchKeyword);

    if (nextSearchKeyword === searchKeyword) {
      await loadUsers();
    }
  };

  /**
   * 发送客户邮件。
   *
   * Returns:
   *   无返回值
   */
  const handleSend = async (): Promise<void> => {
    if (selectedEmails.size === 0) {
      toast.error('Please select at least one recipient');
      return;
    }

    if (!subject.trim() || !htmlContent.trim() || !textContent.trim()) {
      toast.error('Subject, HTML template, and Markdown content are required');
      return;
    }

    try {
      setIsSending(true);
      const response = await apiClient.post<CustomerEmailSendResponse>(
        '/admin/customer-emails/send',
        {
          recipient_emails: Array.from(selectedEmails),
          subject: subject.trim(),
          html_content: htmlContent.trim(),
          text_content: textContent.trim() || null,
          template_key: templateKey,
        }
      );

      const { success, failed, errors } = response.data;

      if (failed === 0) {
        toast.success(`Successfully sent ${success} email${success > 1 ? 's' : ''}`);
      } else {
        toast.warning(`Sent ${success} email${success > 1 ? 's' : ''}, ${failed} failed`, {
          description: errors.map((item) => `${item.email}: ${item.error}`).join('\n'),
          duration: 8000,
        });
      }
    } catch (error) {
      console.error('Failed to send customer emails:', error);
      toast.error('Failed to send customer emails');
    } finally {
      setIsSending(false);
    }
  };

  const allSelected = useMemo(() => {
    if (users.length === 0) {
      return false;
    }

    return selectedEmails.size === users.length;
  }, [selectedEmails, users]);

  const previewHtml = useMemo(() => {
    return composeEmailHtml(
      htmlContent.trim() || DEFAULT_EMAIL_TEMPLATE_SHELL,
      subject.trim() || 'No subject yet',
      textContent,
      '#'
    );
  }, [htmlContent, subject, textContent]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <div className="mb-2 flex items-center gap-3">
            <Megaphone className="h-8 w-8 text-sage-600" />
            <h1 className="text-4xl font-serif font-semibold text-foreground">
              Customer Emails
            </h1>
          </div>
          <p className="text-muted-foreground">
            Compose emails with a reusable HTML template shell and a Markdown body.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recipient Filters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[280px] flex-1 space-y-2">
                <Label htmlFor="customer-email-search">Search users</Label>
                <div className="flex gap-2">
                  <Input
                    id="customer-email-search"
                    value={keyword}
                    onChange={(event) => setKeyword(event.target.value)}
                    placeholder="Search by email or username"
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        void handleSearch();
                      }
                    }}
                  />
                  <Button onClick={() => void handleSearch()} variant="outline" className="gap-2">
                    <Search className="h-4 w-4" />
                    Search
                  </Button>
                </div>
              </div>

              <div className="w-[180px] space-y-2">
                <Label>Status</Label>
                <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StatusFilter)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                checked={includeSuperusers}
                onCheckedChange={(checked) => setIncludeSuperusers(Boolean(checked))}
              />
              <span className="text-sm text-foreground">Include superusers</span>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Card className="overflow-hidden">
            <CardHeader className="border-b">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <CardTitle>Recipients</CardTitle>
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span>Total: {total}</span>
                  <span>Selected: {selectedEmails.size}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {isLoadingUsers ? (
                <div className="p-6">
                  <TableSkeleton rows={6} columns={6} />
                </div>
              ) : users.length === 0 ? (
                <div className="p-12 text-center">
                  <Mail className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
                  <h3 className="mb-2 text-lg font-medium text-foreground">No users found</h3>
                  <p className="text-sm text-muted-foreground">
                    Adjust the filters or search keyword and try again.
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <Checkbox checked={allSelected} onCheckedChange={toggleSelectAll} />
                      </TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Username</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((item) => (
                      <TableRow key={item.email}>
                        <TableCell>
                          <Checkbox
                            checked={selectedEmails.has(item.email)}
                            onCheckedChange={() => toggleSelect(item.email)}
                          />
                        </TableCell>
                        <TableCell className="font-medium">{item.email}</TableCell>
                        <TableCell>{item.username || '-'}</TableCell>
                        <TableCell>
                          {item.is_active ? (
                            <Badge variant="sage">Active</Badge>
                          ) : (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {item.is_superuser ? (
                            <Badge variant="outline">Superuser</Badge>
                          ) : (
                            <Badge variant="outline">User</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(item.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Email Composer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Template</Label>
                  <Select
                    value={templateKey}
                    onValueChange={handleTemplateChange}
                    disabled={isLoadingTemplates}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a template" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="custom">Custom</SelectItem>
                      {templates.map((template) => (
                        <SelectItem key={template.key} value={template.key}>
                          {template.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {templateKey !== 'custom' && (
                    <p className="text-sm text-muted-foreground">
                      {templates.find((item) => item.key === templateKey)?.description}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email-subject">Subject</Label>
                  <Input
                    id="email-subject"
                    value={subject}
                    onChange={(event) => setSubject(event.target.value)}
                    placeholder="Enter email subject"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email-html-content">HTML Template</Label>
                  <p className="text-xs text-muted-foreground">
                    Edit the email shell here. Keep <code>{'{{subject}}'}</code> and <code>{'{{content}}'}</code> so the final email can render correctly.
                  </p>
                  <Textarea
                    id="email-html-content"
                    value={htmlContent}
                    onChange={(event) => setHtmlContent(event.target.value)}
                    placeholder="Enter HTML email template"
                    className="min-h-[260px] font-mono text-xs"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email-text-content">Plain Text Content (Markdown)</Label>
                  <p className="text-xs text-muted-foreground">
                    Write the actual email body here in Markdown. It will be rendered into the HTML template above.
                  </p>
                  <Textarea
                    id="email-text-content"
                    value={textContent}
                    onChange={(event) => setTextContent(event.target.value)}
                    placeholder="Write Markdown content here"
                    className="min-h-[180px]"
                  />
                </div>

                <Button
                  onClick={() => void handleSend()}
                  disabled={selectedEmails.size === 0 || isSending}
                  className="w-full gap-2"
                >
                  <Send className="h-4 w-4" />
                  {isSending ? 'Sending...' : `Send to ${selectedEmails.size || 0} selected user${selectedEmails.size === 1 ? '' : 's'}`}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Preview</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">Subject</p>
                  <p className="text-base font-medium text-foreground">
                    {subject.trim() || 'No subject yet'}
                  </p>
                </div>
                <iframe
                  title="Email preview"
                  srcDoc={previewHtml}
                  className="h-[720px] w-full rounded-lg border border-border bg-white"
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

