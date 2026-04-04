import type { Metadata } from 'next';

import { RoadmapTimeline } from '@/components/roadmap/public/roadmap-timeline';
import { VotingBoard } from '@/components/roadmap/public/voting-board';

/**
 * 产品路书页面 SEO
 */
export const metadata: Metadata = {
  title: 'Product Roadmap | Fast Learning',
  description:
    'Explore released milestones, features in progress, upcoming plans, and community-voted ideas for Fast Learning.',
};

/**
 * 产品路书页
 */
export default function ProductRoadmapPage() {
  return (
    <>
      <RoadmapTimeline />
      <VotingBoard />
    </>
  );
}
