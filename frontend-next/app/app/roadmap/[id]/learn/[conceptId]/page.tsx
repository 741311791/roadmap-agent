'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  BookOpen,
  FileQuestion,
  ExternalLink,
  ListTree,
  PanelLeft,
} from 'lucide-react';

// Mock data - would come from API/store in real app
const mockConcept = {
  concept_id: 'c1',
  name: 'HTML Structure & Semantics',
  description: 'Learn semantic HTML elements and document structure',
  estimated_hours: 3,
  difficulty: 'easy' as const,
  keywords: ['html', 'semantic', 'structure', 'accessibility'],
  stageName: 'Frontend Fundamentals',
  moduleName: 'HTML & CSS',
};

const mockTutorial = `
# HTML Structure & Semantics

## Introduction

HTML (HyperText Markup Language) is the backbone of every web page. Understanding semantic HTML is crucial for creating accessible, SEO-friendly, and maintainable websites.

## What is Semantic HTML?

Semantic HTML uses elements that clearly describe their meaning to both the browser and the developer. Instead of using generic \`<div>\` elements everywhere, we use elements that convey the purpose of their content.

### Key Semantic Elements

- \`<header>\` - Introductory content or navigational links
- \`<nav>\` - Navigation links
- \`<main>\` - Main content of the document
- \`<article>\` - Self-contained composition
- \`<section>\` - Thematic grouping of content
- \`<aside>\` - Sidebar or tangential content
- \`<footer>\` - Footer content

## Document Structure

A well-structured HTML document follows this pattern:

\`\`\`html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Page</title>
</head>
<body>
  <header>
    <nav><!-- Navigation --></nav>
  </header>
  <main>
    <article>
      <h1>Article Title</h1>
      <section><!-- Content --></section>
    </article>
    <aside><!-- Sidebar --></aside>
  </main>
  <footer><!-- Footer --></footer>
</body>
</html>
\`\`\`

## Why Semantic HTML Matters

1. **Accessibility**: Screen readers can better navigate semantic content
2. **SEO**: Search engines understand the structure better
3. **Maintainability**: Code is easier to read and maintain
4. **Mobile**: Better rendering on different devices

## Best Practices

> "The purpose of semantic HTML is to give meaning to content, not to define its visual appearance."

- Use \`<h1>\` through \`<h6>\` in hierarchical order
- Don't skip heading levels
- Use \`<p>\` for paragraphs, not for spacing
- Use lists (\`<ul>\`, \`<ol>\`) for related items
- Use \`<figure>\` and \`<figcaption>\` for images with captions

## Conclusion

Mastering semantic HTML is the foundation of professional web development. It improves accessibility, SEO, and code quality—making your websites better for everyone.
`;

const mockQuiz = [
  {
    question_id: 'q1',
    question: 'Which element should be used for the main navigation of a website?',
    question_type: 'single_choice',
    options: ['<div class="nav">', '<nav>', '<menu>', '<navigation>'],
    correct_answer: [1],
    explanation: 'The <nav> element is specifically designed for major navigation blocks.',
  },
  {
    question_id: 'q2',
    question: 'What is the primary benefit of using semantic HTML?',
    question_type: 'single_choice',
    options: [
      'Better visual styling',
      'Faster page loading',
      'Improved accessibility and SEO',
      'Smaller file size',
    ],
    correct_answer: [2],
    explanation: 'Semantic HTML primarily benefits accessibility for screen readers and SEO for search engines.',
  },
];

const mockResources = [
  {
    title: 'MDN Web Docs - HTML',
    url: 'https://developer.mozilla.org/en-US/docs/Web/HTML',
    type: 'documentation',
    description: 'Comprehensive HTML documentation from Mozilla',
  },
  {
    title: 'HTML Best Practices',
    url: 'https://www.w3schools.com/html/html5_semantic_elements.asp',
    type: 'article',
    description: 'W3Schools guide to semantic elements',
  },
];

export default function LearningPage() {
  const params = useParams();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('tutorial');
  const [isTocCollapsed, setIsTocCollapsed] = useState(false);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  const [showResults, setShowResults] = useState(false);

  const concept = mockConcept;
  const tutorial = mockTutorial;

  // Parse TOC from markdown
  const tocItems = tutorial
    .split('\n')
    .filter((line) => line.startsWith('## '))
    .map((line) => ({
      id: line.replace('## ', '').toLowerCase().replace(/\s+/g, '-'),
      label: line.replace('## ', ''),
    }));

  const handleAnswerSelect = (questionId: string, answerIndex: number) => {
    if (showResults) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [questionId]: answerIndex,
    }));
  };

  const handleSubmitQuiz = () => {
    setShowResults(true);
  };

  const getQuizScore = () => {
    let correct = 0;
    mockQuiz.forEach((q) => {
      if (selectedAnswers[q.question_id] === q.correct_answer[0]) {
        correct++;
      }
    });
    return correct;
  };

  return (
    <div className="flex h-full bg-background">
      {/* TOC Sidebar */}
      <div
        className={`border-r border-border/5 bg-background transition-all duration-300 ${
          isTocCollapsed ? 'w-12' : 'w-64'
        }`}
      >
        <div className="h-14 flex items-center justify-between px-3 border-b border-border/5">
          {!isTocCollapsed && (
            <Link
              href={`/app/roadmap/${params.id}`}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronLeft size={16} />
              <span>Back</span>
            </Link>
          )}
          <button
            onClick={() => setIsTocCollapsed(!isTocCollapsed)}
            className="p-2 hover:bg-muted rounded transition-colors"
          >
            {isTocCollapsed ? (
              <PanelLeft size={16} className="text-muted-foreground" />
            ) : (
              <ListTree size={16} className="text-muted-foreground" />
            )}
          </button>
        </div>

        {!isTocCollapsed && (
          <ScrollArea className="h-[calc(100%-3.5rem)] p-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Table of Contents
            </div>
            <nav className="space-y-1">
              {tocItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    document
                      .getElementById(item.id)
                      ?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="block w-full text-left text-sm py-2 px-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </ScrollArea>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[85ch] mx-auto py-12 px-8">
          {/* Paper Container */}
          <div className="bg-white shadow-sm border border-stone-100 rounded-xl p-12 md:p-16 min-h-[80vh]">
            {/* Header */}
            <header className="mb-12 border-b border-stone-100 pb-8">
              <div className="flex items-center gap-2 text-sm text-sage-600 font-medium mb-4">
                <span className="text-muted-foreground">
                  {concept.stageName} → {concept.moduleName}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-4">
                <Badge variant="sage">{concept.difficulty}</Badge>
                <span className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Clock size={14} /> {concept.estimated_hours}h
                </span>
              </div>
              <h1 className="text-4xl md:text-5xl font-serif font-bold text-stone-900 mb-4 leading-tight">
                {concept.name}
              </h1>
              <p className="text-lg text-stone-500 leading-relaxed">
                {concept.description}
              </p>
            </header>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-8">
                <TabsTrigger value="tutorial" className="gap-2">
                  <BookOpen size={16} /> Tutorial
                </TabsTrigger>
                <TabsTrigger value="quiz" className="gap-2">
                  <FileQuestion size={16} /> Quiz
                </TabsTrigger>
                <TabsTrigger value="resources" className="gap-2">
                  <ExternalLink size={16} /> Resources
                </TabsTrigger>
              </TabsList>

              {/* Tutorial Tab */}
              <TabsContent value="tutorial">
                <article
                  className="prose prose-stone prose-lg max-w-none 
                  prose-headings:font-serif prose-headings:font-bold prose-headings:text-stone-800
                  prose-p:text-stone-600 prose-p:leading-loose
                  prose-blockquote:border-l-sage-400 prose-blockquote:bg-sage-50/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:not-italic prose-blockquote:text-stone-700
                  prose-code:text-sage-700 prose-code:bg-sage-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none
                  prose-pre:bg-stone-900 prose-pre:shadow-lg prose-pre:rounded-xl
                  prose-li:text-stone-600
                  prose-strong:text-stone-800 prose-strong:font-semibold"
                >
                  <ReactMarkdown>{tutorial}</ReactMarkdown>
                </article>
              </TabsContent>

              {/* Quiz Tab */}
              <TabsContent value="quiz">
                <div className="space-y-6">
                  {showResults && (
                    <Card className="bg-sage-50 border-sage-200">
                      <CardContent className="py-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-sage-800">
                              Quiz Results
                            </h3>
                            <p className="text-sage-600">
                              You scored {getQuizScore()} out of {mockQuiz.length}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            onClick={() => {
                              setShowResults(false);
                              setSelectedAnswers({});
                            }}
                          >
                            Retry Quiz
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {mockQuiz.map((question, qIndex) => (
                    <Card key={question.question_id}>
                      <CardHeader>
                        <CardTitle className="text-lg font-medium">
                          {qIndex + 1}. {question.question}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {question.options.map((option, oIndex) => {
                            const isSelected =
                              selectedAnswers[question.question_id] === oIndex;
                            const isCorrect =
                              question.correct_answer[0] === oIndex;
                            const showCorrect = showResults && isCorrect;
                            const showWrong =
                              showResults && isSelected && !isCorrect;

                            return (
                              <button
                                key={oIndex}
                                onClick={() =>
                                  handleAnswerSelect(question.question_id, oIndex)
                                }
                                disabled={showResults}
                                className={`w-full p-4 rounded-lg border text-left transition-colors ${
                                  showCorrect
                                    ? 'border-green-500 bg-green-50'
                                    : showWrong
                                    ? 'border-red-500 bg-red-50'
                                    : isSelected
                                    ? 'border-sage-500 bg-sage-50'
                                    : 'border-border hover:border-sage-300'
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}
                        </div>
                        {showResults && (
                          <p className="mt-4 text-sm text-muted-foreground bg-muted p-4 rounded-lg">
                            <strong>Explanation:</strong> {question.explanation}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  ))}

                  {!showResults && (
                    <Button
                      onClick={handleSubmitQuiz}
                      variant="sage"
                      className="w-full"
                      disabled={
                        Object.keys(selectedAnswers).length < mockQuiz.length
                      }
                    >
                      Submit Quiz
                    </Button>
                  )}
                </div>
              </TabsContent>

              {/* Resources Tab */}
              <TabsContent value="resources">
                <div className="space-y-4">
                  {mockResources.map((resource) => (
                    <a
                      key={resource.url}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-4 rounded-lg border border-border hover:border-sage-300 hover:bg-sage-50/50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-medium text-foreground">
                            {resource.title}
                          </h3>
                          <p className="text-sm text-muted-foreground mt-1">
                            {resource.description}
                          </p>
                        </div>
                        <Badge variant="outline">{resource.type}</Badge>
                      </div>
                    </a>
                  ))}
                </div>
              </TabsContent>
            </Tabs>

            {/* Footer Actions */}
            <div className="mt-16 pt-8 border-t border-stone-100 flex justify-between items-center">
              <span className="text-sm text-muted-foreground">
                Last updated: Just now
              </span>
              <Button variant="sage" className="gap-2">
                Mark as Complete <CheckCircle2 size={16} />
              </Button>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between mt-8">
            <Button variant="outline" className="gap-2">
              <ChevronLeft size={16} /> Previous Concept
            </Button>
            <Button variant="outline" className="gap-2">
              Next Concept <ChevronRight size={16} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

