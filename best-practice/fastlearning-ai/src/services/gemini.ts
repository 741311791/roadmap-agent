export interface RoadmapNode {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'completed';
  children?: RoadmapNode[];
}

export interface Roadmap {
  title: string;
  nodes: RoadmapNode[];
}

export interface LearningContent {
  title: string;
  markdown: string;
  codeSnippets?: { language: string; code: string }[];
}

export interface Quiz {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

// Helper to simulate network latency
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const geminiService = {
  async generateRoadmap(topic: string, background: string): Promise<Roadmap> {
    await delay(1500);
    return {
      title: `Mastering ${topic}`,
      nodes: [
        {
          id: '1',
          title: 'Introduction & Fundamentals',
          description: `Core concepts of ${topic}`,
          status: 'todo',
          children: [
            { id: '1-1', title: 'What is it?', description: 'Basic definition and use cases', status: 'todo' },
            { id: '1-2', title: 'Environment Setup', description: 'Getting your tools ready', status: 'todo' }
          ]
        },
        {
          id: '2',
          title: 'Core Mechanics',
          description: 'Deep dive into the main features',
          status: 'todo',
          children: [
            { id: '2-1', title: 'Syntax & Structure', description: 'How to write it', status: 'todo' },
            { id: '2-2', title: 'Best Practices', description: 'Doing it the right way', status: 'todo' }
          ]
        },
        {
          id: '3',
          title: 'Advanced Topics',
          description: 'Taking it to the next level',
          status: 'todo'
        }
      ]
    };
  },

  async generateContent(nodeTitle: string, context: string): Promise<LearningContent> {
    await delay(2000);
    return {
      title: nodeTitle,
      markdown: `
# Welcome to ${nodeTitle}

This is a comprehensive guide to understanding **${nodeTitle}** in the context of ${context}.

## Key Concepts

1. **First Principle**: Always remember the basics.
2. **Second Principle**: Practice makes perfect.

Here is a detailed explanation of how this works under the hood. It's fascinating how these systems are designed to handle complex scenarios with such elegance.

> "The best way to learn is by doing."

Let's look at a practical example below.
      `,
      codeSnippets: [
        {
          language: 'javascript',
          code: `// Example code for ${nodeTitle}\nfunction init() {\n  console.log("Hello, World!");\n  // Add your logic here\n}\n\ninit();`
        }
      ]
    };
  },

  async generateQuiz(content: string): Promise<Quiz> {
    await delay(1500);
    return {
      question: `Based on the content, what is the most important principle?`,
      options: [
        "Always remember the basics",
        "Copy and paste code",
        "Skip the documentation",
        "None of the above"
      ],
      correctAnswer: 0,
      explanation: "The content explicitly mentions 'Always remember the basics' as the First Principle."
    };
  }
};
