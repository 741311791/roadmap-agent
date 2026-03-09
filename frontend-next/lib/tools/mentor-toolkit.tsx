'use client';

import { ConceptTutorialToolCard } from '@/components/chat/tools/concept-tutorial-tool-card';
import { MarkContentCompleteToolCard } from '@/components/chat/tools/mark-content-complete-tool-card';
import { RoadmapMetadataToolCard } from '@/components/chat/tools/roadmap-metadata-tool-card';
import { UserProfileToolCard } from '@/components/chat/tools/user-profile-tool-card';

interface MentorToolResultRendererProps {
  toolName: string;
  result: unknown;
}

function parseToolResult(result: unknown): Record<string, unknown> | null {
  if (result && typeof result === 'object' && !Array.isArray(result)) {
    return result as Record<string, unknown>;
  }

  if (typeof result === 'string') {
    const text = result.trim();
    if (
      (text.startsWith('{') && text.endsWith('}')) ||
      (text.startsWith('[') && text.endsWith(']'))
    ) {
      try {
        const parsed = JSON.parse(text);
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          return parsed as Record<string, unknown>;
        }
      } catch {
        return null;
      }
    }
  }

  return null;
}

/**
 * Mentor 工具结果渲染器。
 */
export function MentorToolResultRenderer({
  toolName,
  result,
}: MentorToolResultRendererProps) {
  const parsedResult = parseToolResult(result);

  if (!parsedResult) {
    return (
      <p className="text-xs text-muted-foreground break-all">
        {typeof result === 'string' ? result : JSON.stringify(result)}
      </p>
    );
  }

  if (toolName === 'get_roadmap_metadata') {
    return <RoadmapMetadataToolCard result={parsedResult} />;
  }

  if (toolName === 'get_concept_tutorial') {
    return <ConceptTutorialToolCard result={parsedResult} />;
  }

  if (toolName === 'get_user_profile') {
    return <UserProfileToolCard result={parsedResult} />;
  }

  if (toolName === 'mark_content_complete') {
    return <MarkContentCompleteToolCard result={parsedResult} />;
  }

  return (
    <p className="text-xs text-muted-foreground break-all">
      {JSON.stringify(parsedResult)}
    </p>
  );
}
