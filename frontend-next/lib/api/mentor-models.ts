/**
 * Mentor 模型注册表管理接口
 */
import { apiClient } from "@/lib/api/client";

export interface MentorModelAdminItem {
  model_id: string;
  display_name: string;
  description?: string | null;
  provider: string;
  model_name: string;
  base_url: string;
  api_key_masked: string;
  is_active: boolean;
  is_visible: boolean;
  is_default: boolean;
  supports_streaming: boolean;
  supports_structured_output: boolean;
  supports_tools: boolean;
  supports_thinking: boolean;
  scope: "system" | "user";
  owner_user_id?: string | null;
  test_status: "untested" | "passed" | "failed";
  last_tested_at?: string | null;
  last_test_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MentorModelAdminListResponse {
  items: MentorModelAdminItem[];
  total: number;
}

export interface MentorModelCreateRequest {
  display_name: string;
  description?: string | null;
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
  scope: "system" | "user";
  owner_user_id?: string | null;
}

export interface MentorModelUpdateRequest {
  display_name?: string;
  description?: string | null;
  provider?: string;
  model_name?: string;
  base_url?: string;
  api_key?: string;
  is_active?: boolean;
  is_visible?: boolean;
  is_default?: boolean;
  supports_streaming?: boolean;
  supports_structured_output?: boolean;
  supports_tools?: boolean;
  supports_thinking?: boolean;
  scope?: "system" | "user";
  owner_user_id?: string | null;
}

export interface MentorModelDraftTestRequest {
  provider: string;
  model_name: string;
  base_url: string;
  api_key: string;
  supports_streaming: boolean;
  supports_structured_output: boolean;
  supports_thinking: boolean;
}

export interface MentorModelTestResponse {
  success: boolean;
  provider: string;
  model_name: string;
  base_url: string;
  basic_completion_ok: boolean;
  streaming_ok: boolean;
  structured_output_ok: boolean;
  test_status: "untested" | "passed" | "failed";
  error_message?: string | null;
  tested_at: string;
}

export async function listAdminMentorModels(): Promise<MentorModelAdminListResponse> {
  const response = await apiClient.get<MentorModelAdminListResponse>("/admin/mentor-models");
  return response.data;
}

export async function createAdminMentorModel(
  payload: MentorModelCreateRequest
): Promise<MentorModelAdminItem> {
  const response = await apiClient.post<MentorModelAdminItem>("/admin/mentor-models", payload);
  return response.data;
}

export async function updateAdminMentorModel(
  modelId: string,
  payload: MentorModelUpdateRequest
): Promise<MentorModelAdminItem> {
  const response = await apiClient.patch<MentorModelAdminItem>(
    `/admin/mentor-models/${modelId}`,
    payload
  );
  return response.data;
}

export async function deleteAdminMentorModel(modelId: string): Promise<{ model_id: string }> {
  const response = await apiClient.delete<{ model_id: string }>(
    `/admin/mentor-models/${modelId}`
  );
  return response.data;
}

export async function testMentorModelDraft(
  payload: MentorModelDraftTestRequest
): Promise<MentorModelTestResponse> {
  const response = await apiClient.post<MentorModelTestResponse>(
    "/admin/mentor-models/test",
    payload
  );
  return response.data;
}

export async function testRegisteredMentorModel(
  modelId: string
): Promise<MentorModelTestResponse> {
  const response = await apiClient.post<MentorModelTestResponse>(
    `/admin/mentor-models/${modelId}/test`
  );
  return response.data;
}

