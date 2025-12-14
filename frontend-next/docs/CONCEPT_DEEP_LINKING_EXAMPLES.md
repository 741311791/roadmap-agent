# Concept 深度链接使用示例

本文档提供了 Concept 深度链接功能的实际使用示例。

## 📝 基础用法

### 示例 1: 在组件中跳转到特定 Concept

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export function ConceptNavigation() {
  const router = useRouter();

  const navigateToIntroduction = () => {
    const roadmapId = 'roadmap_abc123';
    const conceptId = 'stage_1:module_1:introduction';
    
    // 跳转到特定 Concept
    router.push(
      `/roadmap/${roadmapId}?concept=${encodeURIComponent(conceptId)}`
    );
  };

  return (
    <Button onClick={navigateToIntroduction}>
      Go to Introduction
    </Button>
  );
}
```

### 示例 2: 分享特定 Concept 链接

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Check } from 'lucide-react';

interface ShareConceptButtonProps {
  roadmapId: string;
  conceptId: string;
  conceptName: string;
}

export function ShareConceptButton({ 
  roadmapId, 
  conceptId, 
  conceptName 
}: ShareConceptButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    // 生成完整的 URL
    const url = `${window.location.origin}/roadmap/${roadmapId}?concept=${encodeURIComponent(conceptId)}`;
    
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      
      // 3 秒后恢复图标
      setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleShare}
      className="gap-2"
    >
      {copied ? (
        <>
          <Check className="h-4 w-4" />
          Copied!
        </>
      ) : (
        <>
          <Copy className="h-4 w-4" />
          Share "{conceptName}"
        </>
      )}
    </Button>
  );
}
```

### 示例 3: 在卡片列表中生成深度链接

```tsx
'use client';

import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import type { Concept } from '@/types/generated/models';

interface ConceptCardProps {
  roadmapId: string;
  concept: Concept;
}

export function ConceptCard({ roadmapId, concept }: ConceptCardProps) {
  // 生成深度链接
  const conceptUrl = `/roadmap/${roadmapId}?concept=${encodeURIComponent(concept.concept_id)}`;

  return (
    <Link href={conceptUrl}>
      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
        <CardHeader>
          <CardTitle>{concept.name}</CardTitle>
          <CardDescription>{concept.description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}
```

## 🔄 高级用法

### 示例 4: 带状态的 Concept 导航

```tsx
'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useRoadmapStore } from '@/lib/store/roadmap-store';

export function ConceptNavigator() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { currentRoadmap, selectedConceptId } = useRoadmapStore();

  // 获取下一个 Concept
  const getNextConcept = () => {
    if (!currentRoadmap || !selectedConceptId) return null;
    
    // 获取所有 concepts 的扁平数组
    const allConcepts = currentRoadmap.stages.flatMap(stage =>
      stage.modules.flatMap(module => module.concepts)
    );
    
    // 找到当前 concept 的索引
    const currentIndex = allConcepts.findIndex(
      c => c.concept_id === selectedConceptId
    );
    
    // 返回下一个 concept（如果存在）
    if (currentIndex >= 0 && currentIndex < allConcepts.length - 1) {
      return allConcepts[currentIndex + 1];
    }
    
    return null;
  };

  // 获取上一个 Concept
  const getPreviousConcept = () => {
    if (!currentRoadmap || !selectedConceptId) return null;
    
    const allConcepts = currentRoadmap.stages.flatMap(stage =>
      stage.modules.flatMap(module => module.concepts)
    );
    
    const currentIndex = allConcepts.findIndex(
      c => c.concept_id === selectedConceptId
    );
    
    if (currentIndex > 0) {
      return allConcepts[currentIndex - 1];
    }
    
    return null;
  };

  const navigateToNext = () => {
    const next = getNextConcept();
    if (next && currentRoadmap) {
      router.push(
        `/roadmap/${currentRoadmap.roadmap_id}?concept=${encodeURIComponent(next.concept_id)}`
      );
    }
  };

  const navigateToPrevious = () => {
    const previous = getPreviousConcept();
    if (previous && currentRoadmap) {
      router.push(
        `/roadmap/${currentRoadmap.roadmap_id}?concept=${encodeURIComponent(previous.concept_id)}`
      );
    }
  };

  return (
    <div className="flex gap-2">
      <Button
        onClick={navigateToPrevious}
        disabled={!getPreviousConcept()}
        variant="outline"
      >
        ← Previous
      </Button>
      <Button
        onClick={navigateToNext}
        disabled={!getNextConcept()}
        variant="outline"
      >
        Next →
      </Button>
    </div>
  );
}
```

### 示例 5: 带验证的 URL 参数处理

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { isConceptIdValid } from '@/lib/utils/roadmap-helpers';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export function ConceptValidator() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { currentRoadmap } = useRoadmapStore();
  const [error, setError] = useState<string | null>(null);

  const roadmapId = params.id as string;
  const conceptId = searchParams.get('concept');

  useEffect(() => {
    if (!conceptId) {
      setError(null);
      return;
    }

    if (!currentRoadmap) {
      setError('Loading roadmap...');
      return;
    }

    // 验证 Concept ID
    if (!isConceptIdValid(currentRoadmap, conceptId)) {
      setError(`Invalid concept ID: "${conceptId}"`);
    } else {
      setError(null);
    }
  }, [conceptId, currentRoadmap]);

  if (!error) return null;

  return (
    <Alert variant="destructive" className="m-4">
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>
        {error}
      </AlertDescription>
    </Alert>
  );
}
```

### 示例 6: 生成社交媒体分享链接

```tsx
'use client';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Share2, Twitter, Facebook, Linkedin } from 'lucide-react';

interface SocialShareProps {
  roadmapId: string;
  conceptId: string;
  conceptName: string;
  roadmapTitle: string;
}

export function SocialShareButton({
  roadmapId,
  conceptId,
  conceptName,
  roadmapTitle,
}: SocialShareProps) {
  // 生成深度链接
  const conceptUrl = `${window.location.origin}/roadmap/${roadmapId}?concept=${encodeURIComponent(conceptId)}`;
  
  // 分享文本
  const shareText = `Check out "${conceptName}" from "${roadmapTitle}" roadmap`;

  const shareOnTwitter = () => {
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(conceptUrl)}`;
    window.open(twitterUrl, '_blank');
  };

  const shareOnFacebook = () => {
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(conceptUrl)}`;
    window.open(facebookUrl, '_blank');
  };

  const shareOnLinkedIn = () => {
    const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(conceptUrl)}`;
    window.open(linkedinUrl, '_blank');
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(conceptUrl);
      alert('Link copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Share2 className="h-4 w-4" />
          Share
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={shareOnTwitter}>
          <Twitter className="mr-2 h-4 w-4" />
          Share on Twitter
        </DropdownMenuItem>
        <DropdownMenuItem onClick={shareOnFacebook}>
          <Facebook className="mr-2 h-4 w-4" />
          Share on Facebook
        </DropdownMenuItem>
        <DropdownMenuItem onClick={shareOnLinkedIn}>
          <Linkedin className="mr-2 h-4 w-4" />
          Share on LinkedIn
        </DropdownMenuItem>
        <DropdownMenuItem onClick={copyLink}>
          <Share2 className="mr-2 h-4 w-4" />
          Copy Link
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### 示例 7: 面包屑导航

```tsx
'use client';

import Link from 'next/link';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { findConceptById } from '@/lib/utils/roadmap-helpers';
import { ChevronRight } from 'lucide-react';

interface BreadcrumbsProps {
  roadmapId: string;
}

export function ConceptBreadcrumbs({ roadmapId }: BreadcrumbsProps) {
  const { currentRoadmap, selectedConceptId } = useRoadmapStore();

  if (!currentRoadmap || !selectedConceptId) {
    return null;
  }

  // 查找当前 Concept 及其父级结构
  let stageName = '';
  let moduleName = '';
  let conceptName = '';

  for (const stage of currentRoadmap.stages) {
    for (const module of stage.modules) {
      const concept = module.concepts.find(c => c.concept_id === selectedConceptId);
      if (concept) {
        stageName = stage.name;
        moduleName = module.name;
        conceptName = concept.name;
        break;
      }
    }
  }

  return (
    <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
      <Link
        href={`/roadmap/${roadmapId}`}
        className="hover:text-foreground transition-colors"
      >
        {currentRoadmap.title}
      </Link>
      <ChevronRight className="h-4 w-4" />
      <span>{stageName}</span>
      <ChevronRight className="h-4 w-4" />
      <span>{moduleName}</span>
      <ChevronRight className="h-4 w-4" />
      <span className="text-foreground font-medium">{conceptName}</span>
    </nav>
  );
}
```

## 🎯 实际应用场景

### 场景 1: 教师分享课程链接

```tsx
// 教师可以分享特定章节的链接给学生
const lessonUrl = `/roadmap/intro-to-react?concept=${encodeURIComponent('stage_2:module_3:hooks')}`;

// 学生点击链接后，直接跳转到 "Hooks" 章节，无需手动查找
```

### 场景 2: 学习进度追踪

```tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useRoadmapStore } from '@/lib/store/roadmap-store';

export function ResumeProgress() {
  const router = useRouter();
  const { currentRoadmap } = useRoadmapStore();

  useEffect(() => {
    // 从 localStorage 读取用户上次学习的 Concept
    const lastConceptId = localStorage.getItem('lastConceptId');
    
    if (lastConceptId && currentRoadmap) {
      // 恢复学习进度
      router.push(
        `/roadmap/${currentRoadmap.roadmap_id}?concept=${encodeURIComponent(lastConceptId)}`
      );
    }
  }, [currentRoadmap, router]);

  // 监听 Concept 变化，保存进度
  useEffect(() => {
    const { selectedConceptId } = useRoadmapStore.getState();
    
    if (selectedConceptId) {
      localStorage.setItem('lastConceptId', selectedConceptId);
    }
  }, []);

  return null;
}
```

### 场景 3: 搜索结果跳转

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';
import { useRoadmapStore } from '@/lib/store/roadmap-store';
import { getAllConceptIds, findConceptById } from '@/lib/utils/roadmap-helpers';

export function ConceptSearch() {
  const router = useRouter();
  const { currentRoadmap } = useRoadmapStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<string[]>([]);

  const handleSearch = () => {
    if (!currentRoadmap || !searchTerm) return;

    // 搜索匹配的 Concept IDs
    const allIds = getAllConceptIds(currentRoadmap);
    const matches = allIds.filter(id => {
      const concept = findConceptById(currentRoadmap, id);
      return concept?.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
             concept?.description.toLowerCase().includes(searchTerm.toLowerCase());
    });

    setResults(matches);
  };

  const navigateToConcept = (conceptId: string) => {
    if (currentRoadmap) {
      router.push(
        `/roadmap/${currentRoadmap.roadmap_id}?concept=${encodeURIComponent(conceptId)}`
      );
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="Search concepts..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button onClick={handleSearch} size="icon">
          <Search className="h-4 w-4" />
        </Button>
      </div>

      {results.length > 0 && (
        <ul className="space-y-2">
          {results.map((id) => {
            const concept = findConceptById(currentRoadmap, id);
            return (
              <li key={id}>
                <button
                  onClick={() => navigateToConcept(id)}
                  className="text-left w-full p-2 hover:bg-accent rounded-md transition-colors"
                >
                  <div className="font-medium">{concept?.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {concept?.description}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
```

## 🔐 安全注意事项

### 始终验证 Concept ID

```tsx
// ✅ 推荐：验证后再使用
const concept = findConceptById(roadmap, conceptId);
if (concept) {
  // 安全地使用 concept
}

// ❌ 不推荐：直接使用未验证的 ID
const concept = roadmap.stages[0].modules[0].concepts.find(c => c.concept_id === conceptId);
// 可能导致运行时错误
```

### 防止 XSS 攻击

```tsx
// ✅ 推荐：使用 encodeURIComponent
const url = `/roadmap/${roadmapId}?concept=${encodeURIComponent(userInput)}`;

// ❌ 不推荐：直接拼接用户输入
const url = `/roadmap/${roadmapId}?concept=${userInput}`;
// 可能导致 XSS 攻击
```

## 📚 相关资源

- [Concept 深度链接与性能优化文档](../../../CONCEPT_DEEP_LINKING_AND_PERFORMANCE.md)
- [路线图辅助工具函数](../lib/utils/roadmap-helpers.ts)
- [路线图状态管理](../lib/store/roadmap-store.ts)
