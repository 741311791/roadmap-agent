'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bot, Loader2, Pencil, Plus, RefreshCw, TestTube2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  createAdminMentorModel,
  deleteAdminMentorModel,
  listAdminMentorModels,
  testMentorModelDraft,
  testRegisteredMentorModel,
  updateAdminMentorModel,
  type MentorModelAdminItem,
  type MentorModelCreateRequest,
  type MentorModelDraftTestRequest,
  type MentorModelTestResponse,
  type MentorModelUpdateRequest,
} from '@/lib/api/mentor-models';

interface MentorModelFormState {
  display_name: string;
  description: string;
  provider: string;
  model_name: string;
  base_url: string;
  api_key: string;
  is_active: boolean;
  is_visible: boolean;
  is_default: boolean;
  supports_streaming: boolean;
  supports_structured_output: boolean;
  supports_tools: boolean;
  supports_thinking: boolean;
  scope: 'system' | 'user';
  owner_user_id: string;
}

const INITIAL_FORM_STATE: MentorModelFormState = {
  display_name: '',
  description: '',
  provider: 'openai',
  model_name: '',
  base_url: '',
  api_key: '',
  is_active: true,
  is_visible: true,
  is_default: false,
  supports_streaming: true,
  supports_structured_output: true,
  supports_tools: false,
  supports_thinking: false,
  scope: 'system',
  owner_user_id: '',
};

/**
 * formatDateTime - 格式化日期时间
 */
function formatDateTime(dateValue?: string | null): string {
  if (!dateValue) {
    return 'N/A';
  }

  return new Date(dateValue).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * getTestStatusBadge - 渲染测试状态徽标
 */
function getTestStatusBadge(status: MentorModelAdminItem['test_status']) {
  if (status === 'passed') {
    return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Passed</Badge>;
  }
  if (status === 'failed') {
    return <Badge variant="destructive">Failed</Badge>;
  }
  return <Badge variant="secondary">Untested</Badge>;
}

export default function MentorModelsAdminPage() {
  const [models, setModels] = useState<MentorModelAdminItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDraftTesting, setIsDraftTesting] = useState(false);
  const [testingModelId, setTestingModelId] = useState<string | null>(null);
  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);
  const [editingModelId, setEditingModelId] = useState<string | null>(null);
  const [formState, setFormState] = useState<MentorModelFormState>(INITIAL_FORM_STATE);
  const [latestTestResult, setLatestTestResult] = useState<MentorModelTestResponse | null>(null);

  const editingModel = useMemo(
    () => models.find((model) => model.model_id === editingModelId) ?? null,
    [editingModelId, models]
  );

  /**
   * loadModels - 拉取模型注册表
   */
  const loadModels = async () => {
    try {
      setIsLoading(true);
      const response = await listAdminMentorModels();
      setModels(response.items);
    } catch (error) {
      console.error('[MentorModelsAdminPage] Failed to load models:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to load mentor models.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadModels();
  }, []);

  /**
   * resetForm - 重置表单状态
   */
  const resetForm = () => {
    setEditingModelId(null);
    setFormState(INITIAL_FORM_STATE);
    setLatestTestResult(null);
  };

  /**
   * handleEditModel - 将模型数据写入表单
   */
  const handleEditModel = (model: MentorModelAdminItem) => {
    setEditingModelId(model.model_id);
    setFormState({
      display_name: model.display_name,
      description: model.description ?? '',
      provider: model.provider,
      model_name: model.model_name,
      base_url: model.base_url,
      api_key: '',
      is_active: model.is_active,
      is_visible: model.is_visible,
      is_default: model.is_default,
      supports_streaming: model.supports_streaming,
      supports_structured_output: model.supports_structured_output,
      supports_tools: model.supports_tools,
      supports_thinking: model.supports_thinking,
      scope: model.scope,
      owner_user_id: model.owner_user_id ?? '',
    });
    setLatestTestResult(null);
  };

  /**
   * updateFormState - 更新单个表单字段
   */
  const updateFormState = <K extends keyof MentorModelFormState>(
    key: K,
    value: MentorModelFormState[K]
  ) => {
    setFormState((previousState) => ({
      ...previousState,
      [key]: value,
    }));
  };

  /**
   * buildCreatePayload - 构造创建请求
   */
  const buildCreatePayload = (): MentorModelCreateRequest => ({
    display_name: formState.display_name.trim(),
    description: formState.description.trim() || null,
    provider: formState.provider.trim(),
    model_name: formState.model_name.trim(),
    base_url: formState.base_url.trim(),
    api_key: formState.api_key.trim(),
    is_active: formState.is_active,
    is_visible: formState.is_visible,
    is_default: formState.is_default,
    supports_streaming: formState.supports_streaming,
    supports_structured_output: formState.supports_structured_output,
    supports_tools: formState.supports_tools,
    supports_thinking: formState.supports_thinking,
    scope: formState.scope,
    owner_user_id: formState.scope === 'user' ? formState.owner_user_id.trim() || null : null,
  });

  /**
   * buildUpdatePayload - 构造更新请求
   */
  const buildUpdatePayload = (): MentorModelUpdateRequest => {
    const payload: MentorModelUpdateRequest = {
      display_name: formState.display_name.trim(),
      description: formState.description.trim() || null,
      provider: formState.provider.trim(),
      model_name: formState.model_name.trim(),
      base_url: formState.base_url.trim(),
      is_active: formState.is_active,
      is_visible: formState.is_visible,
      is_default: formState.is_default,
      supports_streaming: formState.supports_streaming,
      supports_structured_output: formState.supports_structured_output,
      supports_tools: formState.supports_tools,
      supports_thinking: formState.supports_thinking,
      scope: formState.scope,
      owner_user_id: formState.scope === 'user' ? formState.owner_user_id.trim() || null : null,
    };

    if (formState.api_key.trim()) {
      payload.api_key = formState.api_key.trim();
    }

    return payload;
  };

  /**
   * validateForm - 校验关键字段
   */
  const validateForm = (): boolean => {
    if (!formState.display_name.trim()) {
      toast.error('Display name is required.');
      return false;
    }
    if (!formState.model_name.trim()) {
      toast.error('Model name is required.');
      return false;
    }
    if (!formState.base_url.trim()) {
      toast.error('Base URL is required.');
      return false;
    }
    if (!editingModelId && !formState.api_key.trim()) {
      toast.error('API key is required when creating a model.');
      return false;
    }
    if (formState.scope === 'user' && !formState.owner_user_id.trim()) {
      toast.error('Owner user ID is required for user-scoped models.');
      return false;
    }
    return true;
  };

  /**
   * handleSubmit - 创建或更新模型
   */
  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setIsSubmitting(true);
      if (editingModelId) {
        await updateAdminMentorModel(editingModelId, buildUpdatePayload());
        toast.success('Model updated successfully.');
      } else {
        await createAdminMentorModel(buildCreatePayload());
        toast.success('Model created successfully.');
      }
      await loadModels();
      resetForm();
    } catch (error) {
      console.error('[MentorModelsAdminPage] Failed to save model:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to save mentor model.');
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * handleDraftTest - 测试草稿配置
   */
  const handleDraftTest = async () => {
    if (!formState.model_name.trim() || !formState.base_url.trim() || !formState.api_key.trim()) {
      toast.error('Model name, Base URL and API key are required for draft testing.');
      return;
    }

    try {
      setIsDraftTesting(true);
      const payload: MentorModelDraftTestRequest = {
        provider: formState.provider.trim(),
        model_name: formState.model_name.trim(),
        base_url: formState.base_url.trim(),
        api_key: formState.api_key.trim(),
        supports_streaming: formState.supports_streaming,
        supports_structured_output: formState.supports_structured_output,
        supports_thinking: formState.supports_thinking,
      };
      const result = await testMentorModelDraft(payload);
      setLatestTestResult(result);
      toast.success(result.success ? 'Draft test passed.' : 'Draft test failed.');
    } catch (error) {
      console.error('[MentorModelsAdminPage] Failed to test draft model:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to test draft model.');
    } finally {
      setIsDraftTesting(false);
    }
  };

  /**
   * handleRegisteredTest - 测试已保存模型
   */
  const handleRegisteredTest = async (modelId: string) => {
    try {
      setTestingModelId(modelId);
      const result = await testRegisteredMentorModel(modelId);
      if (editingModelId === modelId) {
        setLatestTestResult(result);
      }
      toast.success(result.success ? 'Model test passed.' : 'Model test failed.');
      await loadModels();
    } catch (error) {
      console.error('[MentorModelsAdminPage] Failed to test registered model:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to test registered model.');
    } finally {
      setTestingModelId(null);
    }
  };

  /**
   * handleDeleteModel - 删除模型
   */
  const handleDeleteModel = async (modelId: string) => {
    try {
      setDeletingModelId(modelId);
      await deleteAdminMentorModel(modelId);
      toast.success('Model deleted successfully.');
      await loadModels();
      if (editingModelId === modelId) {
        resetForm();
      }
    } catch (error) {
      console.error('[MentorModelsAdminPage] Failed to delete model:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to delete mentor model.');
    } finally {
      setDeletingModelId(null);
    }
  };

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <h1 className="flex items-center gap-3 text-4xl font-serif font-bold text-charcoal">
              <Bot className="w-8 h-8 text-sage-600" />
              Mentor Models
            </h1>
            <p className="text-muted-foreground">
              Register, test and manage OpenAI-compatible models for Mentor runtime.
            </p>
          </div>

          <Button onClick={loadModels} disabled={isLoading} variant="outline" className="gap-2">
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle>{editingModel ? 'Edit Model' : 'Register Model'}</CardTitle>
              <CardDescription>
                Keep `model_name` unchanged and let the backend resolve runtime config by `model_id`.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={formState.display_name}
                  onChange={(event) => updateFormState('display_name', event.target.value)}
                  placeholder="Gemini 3.1 Pro Preview"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formState.description}
                  onChange={(event) => updateFormState('description', event.target.value)}
                  placeholder="Optional notes for admins."
                  rows={3}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="provider">Provider</Label>
                  <Input
                    id="provider"
                    value={formState.provider}
                    onChange={(event) => updateFormState('provider', event.target.value)}
                    placeholder="openai"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Scope</Label>
                  <Select
                    value={formState.scope}
                    onValueChange={(value: 'system' | 'user') => updateFormState('scope', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="system">system</SelectItem>
                      <SelectItem value="user">user</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="model_name">Model Name</Label>
                <Input
                  id="model_name"
                  value={formState.model_name}
                  onChange={(event) => updateFormState('model_name', event.target.value)}
                  placeholder="anthropic/claude-sonnet-4"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="base_url">Base URL</Label>
                <Input
                  id="base_url"
                  value={formState.base_url}
                  onChange={(event) => updateFormState('base_url', event.target.value)}
                  placeholder="https://api.example.com/v1"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="api_key">
                  API Key {editingModel ? <span className="text-muted-foreground">(leave blank to keep current)</span> : null}
                </Label>
                <Input
                  id="api_key"
                  type="password"
                  value={formState.api_key}
                  onChange={(event) => updateFormState('api_key', event.target.value)}
                  placeholder={editingModel ? editingModel.api_key_masked : 'sk-...'}
                />
              </div>

              {formState.scope === 'user' ? (
                <div className="space-y-2">
                  <Label htmlFor="owner_user_id">Owner User ID</Label>
                  <Input
                    id="owner_user_id"
                    value={formState.owner_user_id}
                    onChange={(event) => updateFormState('owner_user_id', event.target.value)}
                    placeholder="User UUID"
                  />
                </div>
              ) : null}

              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.is_active}
                    onCheckedChange={(checked) => updateFormState('is_active', checked === true)}
                  />
                  <span>Active</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.is_visible}
                    onCheckedChange={(checked) => updateFormState('is_visible', checked === true)}
                  />
                  <span>Visible in Mentor</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.is_default}
                    onCheckedChange={(checked) => updateFormState('is_default', checked === true)}
                  />
                  <span>Default model</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.supports_streaming}
                    onCheckedChange={(checked) => updateFormState('supports_streaming', checked === true)}
                  />
                  <span>Streaming</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.supports_structured_output}
                    onCheckedChange={(checked) =>
                      updateFormState('supports_structured_output', checked === true)
                    }
                  />
                  <span>Structured output</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.supports_tools}
                    onCheckedChange={(checked) => updateFormState('supports_tools', checked === true)}
                  />
                  <span>Tools</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={formState.supports_thinking}
                    onCheckedChange={(checked) => updateFormState('supports_thinking', checked === true)}
                  />
                  <span>Thinking</span>
                </label>
              </div>

              {latestTestResult ? (
                <div className="rounded-xl border border-border/70 bg-muted/40 p-4 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">Latest Test Result</div>
                    {latestTestResult.success ? (
                      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Passed</Badge>
                    ) : (
                      <Badge variant="destructive">Failed</Badge>
                    )}
                  </div>
                  <div className="mt-3 grid gap-2 text-muted-foreground">
                    <div>Basic completion: {latestTestResult.basic_completion_ok ? 'OK' : 'Failed'}</div>
                    <div>Streaming: {latestTestResult.streaming_ok ? 'OK' : 'Skipped or failed'}</div>
                    <div>
                      Structured output: {latestTestResult.structured_output_ok ? 'OK' : 'Skipped or failed'}
                    </div>
                    <div>Tested at: {formatDateTime(latestTestResult.tested_at)}</div>
                    {latestTestResult.error_message ? (
                      <div className="text-red-600">{latestTestResult.error_message}</div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <Button onClick={handleSubmit} disabled={isSubmitting} className="gap-2">
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  {editingModel ? 'Save Changes' : 'Create Model'}
                </Button>

                <Button onClick={handleDraftTest} disabled={isDraftTesting} variant="outline" className="gap-2">
                  {isDraftTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube2 className="w-4 h-4" />}
                  Test Draft
                </Button>

                {(editingModel || latestTestResult) ? (
                  <Button onClick={resetForm} variant="ghost">
                    Reset
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Registered Models</CardTitle>
              <CardDescription>
                Current models available to the Mentor runtime. Hidden or inactive entries stay visible here for admin review.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Loading models...
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Provider</TableHead>
                      <TableHead>Base URL</TableHead>
                      <TableHead>Last Tested</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {models.map((model) => (
                      <TableRow key={model.model_id}>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-medium">{model.display_name}</span>
                              {model.is_default ? <Badge>Default</Badge> : null}
                              {!model.is_active ? <Badge variant="secondary">Inactive</Badge> : null}
                              {!model.is_visible ? <Badge variant="secondary">Hidden</Badge> : null}
                            </div>
                            <div className="text-xs text-muted-foreground">{model.model_name}</div>
                            <div className="text-xs text-muted-foreground">{model.api_key_masked}</div>
                          </div>
                        </TableCell>
                        <TableCell>{getTestStatusBadge(model.test_status)}</TableCell>
                        <TableCell>{model.provider}</TableCell>
                        <TableCell className="max-w-[220px] truncate">{model.base_url}</TableCell>
                        <TableCell>
                          <div className="text-sm">{formatDateTime(model.last_tested_at)}</div>
                          {model.last_test_error ? (
                            <div className="mt-1 text-xs text-red-600 line-clamp-2">{model.last_test_error}</div>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              onClick={() => handleEditModel(model)}
                              title="Edit model"
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              onClick={() => handleRegisteredTest(model.model_id)}
                              disabled={testingModelId === model.model_id}
                              title="Test model"
                            >
                              {testingModelId === model.model_id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <TestTube2 className="w-4 h-4" />
                              )}
                            </Button>
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              onClick={() => setDeletingModelId(model.model_id)}
                              title="Delete model"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {models.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="py-12 text-center text-muted-foreground">
                          No mentor models have been registered yet.
                        </TableCell>
                      </TableRow>
                    ) : null}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <AlertDialog open={Boolean(deletingModelId)} onOpenChange={(open) => !open && setDeletingModelId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete model?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the selected Mentor model configuration from the registry.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                if (!deletingModelId) {
                  return;
                }
                void handleDeleteModel(deletingModelId);
              }}
              disabled={!deletingModelId}
            >
              {deletingModelId ? 'Delete' : 'Confirm'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

