'use client';

/**
 * 用户评价组件
 * 
 * 基于用户提供的 testimonial 模板
 * 3 列自动滚动，不同速度
 * 使用全局设计令牌
 */

import React from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { motion } from 'motion/react';

interface Testimonial {
  text: string;
  image: string;
  name: string;
  role: string;
}

function TestimonialsColumn({
  testimonials,
  duration = 20,
  className = '',
}: {
  testimonials: Testimonial[];
  duration?: number;
  className?: string;
}) {
  return (
    <div className={className}>
      <motion.ul
        animate={{
          translateY: '-50%',
        }}
        transition={{
          duration,
          repeat: Infinity,
          ease: 'linear',
          repeatType: 'loop',
        }}
        className="flex flex-col gap-6 pb-6 list-none m-0 p-0"
      >
        {[...Array(2)].map((_, duplicateIndex) => (
          <React.Fragment key={duplicateIndex}>
            {testimonials.map((testimonial, index) => (
              <motion.li
                key={`${duplicateIndex}-${index}`}
                aria-hidden={duplicateIndex === 1}
                tabIndex={duplicateIndex === 1 ? -1 : 0}
                whileHover={{
                  scale: 1.03,
                  y: -8,
                  boxShadow:
                    '0 25px 50px -12px hsl(var(--accent) / 0.25), 0 10px 10px -5px hsl(var(--accent) / 0.1)',
                  transition: { type: 'spring', stiffness: 400, damping: 17 },
                }}
                className="p-6 rounded-2xl border border-border glass-panel max-w-xs w-full transition-all duration-300 cursor-default select-none group focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <blockquote className="m-0 p-0">
                  <p className="text-muted-foreground leading-relaxed font-normal m-0 text-sm">
                    {testimonial.text}
                  </p>
                  <footer className="flex items-center gap-3 mt-4">
                    <img
                      width={40}
                      height={40}
                      src={testimonial.image}
                      alt={`Avatar of ${testimonial.name}`}
                      className="h-10 w-10 rounded-full object-cover ring-2 ring-border group-hover:ring-accent transition-all duration-300"
                    />
                    <div className="flex flex-col">
                      <cite className="font-semibold not-italic text-foreground text-sm">
                        {testimonial.name}
                      </cite>
                      <span className="text-xs text-muted-foreground mt-0.5">{testimonial.role}</span>
                    </div>
                  </footer>
                </blockquote>
              </motion.li>
            ))}
          </React.Fragment>
        ))}
      </motion.ul>
    </div>
  );
}

const testimonialsDataEn: Testimonial[] = [
  {
    text: 'Fast Learning transformed how I learn. The AI-generated roadmap was spot-on for my career transition from marketing to data science.',
    image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Sarah Chen',
    role: 'Data Scientist',
  },
  {
    text: 'The personalized approach helped me master React in half the time I expected. Every concept built perfectly on the last.',
    image: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Michael Rodriguez',
    role: 'Frontend Developer',
  },
  {
    text: 'As a self-taught developer, I always struggled with structure. This platform gave me the clear path I was missing.',
    image: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Emily Watson',
    role: 'Full Stack Developer',
  },
  {
    text: 'The adaptive quizzes and curated resources saved me countless hours of research. Everything I needed was right there.',
    image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'David Kim',
    role: 'Software Engineer',
  },
  {
    text: 'I love how the AI understands my learning pace. It never felt too easy or overwhelming, just perfectly challenging.',
    image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Jessica Martinez',
    role: 'Product Manager',
  },
  {
    text: 'The structured approach with clear milestones kept me motivated. I could see my progress every single day.',
    image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Alex Thompson',
    role: 'DevOps Engineer',
  },
  {
    text: 'Coming from a non-tech background, I was intimidated. But Fast Learning made complex topics accessible and engaging.',
    image: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Ryan Park',
    role: 'Career Changer',
  },
  {
    text: 'The tutorial quality is exceptional. Real-world examples and hands-on exercises made learning practical and fun.',
    image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'Olivia Brown',
    role: 'UX Engineer',
  },
  {
    text: 'Best investment in my education. The personalized roadmap helped me land my dream job in just 3 months.',
    image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150&h=150',
    name: 'James Wilson',
    role: 'Backend Developer',
  },
];

const testimonialsDataZh: Testimonial[] = [
  {
    text: 'Fast Learning改变了我的学习方式。AI生成的路线图非常精准，帮助我从市场营销成功转型到数据科学。',
    image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150&h=150',
    name: '陈莎拉',
    role: '数据科学家',
  },
  {
    text: '个性化的方法帮我以预期一半的时间掌握了React。每个概念都完美衔接。',
    image: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&q=80&w=150&h=150',
    name: '迈克尔·罗德里格斯',
    role: '前端工程师',
  },
  {
    text: '作为自学开发者，我一直缺乏系统性。这个平台给了我一直缺失的清晰路径。',
    image: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&q=80&w=150&h=150',
    name: '艾米莉·沃森',
    role: '全栈工程师',
  },
  {
    text: '自适应测验和精选资源为我节省了无数研究时间。所有需要的内容都在这里。',
    image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=150&h=150',
    name: '大卫·金',
    role: '软件工程师',
  },
  {
    text: '我喜欢AI理解我的学习节奏。从不会太简单或太难，总是恰到好处的挑战。',
    image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=150&h=150',
    name: '杰西卡·马丁内斯',
    role: '产品经理',
  },
  {
    text: '清晰的里程碑式方法让我保持动力。我能看到每天的进步。',
    image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&q=80&w=150&h=150',
    name: '亚历克斯·汤普森',
    role: 'DevOps工程师',
  },
  {
    text: '来自非技术背景的我曾感到畏惧。但Fast Learning让复杂话题变得易懂且引人入胜。',
    image: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=150&h=150',
    name: '瑞安·朴',
    role: '职业转型者',
  },
  {
    text: '教程质量卓越。真实案例和动手练习让学习既实用又有趣。',
    image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150&h=150',
    name: '奥利维亚·布朗',
    role: 'UX工程师',
  },
  {
    text: '我教育投资中最好的选择。个性化路线图帮我在短短3个月内找到了梦想工作。',
    image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150&h=150',
    name: '詹姆斯·威尔逊',
    role: '后端工程师',
  },
];

export function TestimonialsSection() {
  const t = useTranslations('testimonials');
  const locale = useLocale();
  
  // 根据当前语言选择评价数据
  const testimonials = locale === 'zh' ? testimonialsDataZh : testimonialsDataEn;
  
  const firstColumn = testimonials.slice(0, 3);
  const secondColumn = testimonials.slice(3, 6);
  const thirdColumn = testimonials.slice(6, 9);
  
  return (
    <section aria-labelledby="testimonials-heading" className="py-24 relative overflow-hidden bg-card">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.15 }}
        transition={{
          duration: 0.8,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="container px-6 z-10 mx-auto max-w-7xl"
      >
        <div className="flex flex-col items-center justify-center max-w-2xl mx-auto mb-16">
          <div className="flex justify-center">
            <div className="border border-border py-1.5 px-4 rounded-full text-xs font-semibold tracking-wide uppercase text-sage bg-muted">
              {t('sectionBadge')}
            </div>
          </div>

          <h2
            id="testimonials-heading"
            className="text-4xl md:text-5xl font-serif font-bold tracking-tight mt-6 text-center text-foreground"
          >
            {t('sectionTitle')}
          </h2>
          <p className="text-center mt-5 text-muted-foreground text-lg leading-relaxed max-w-xl">
            {t('sectionDesc')}
          </p>
        </div>

        <div
          className="flex justify-center gap-6 mt-10 [mask-image:linear-gradient(to_bottom,transparent,black_10%,black_90%,transparent)] max-h-[740px] overflow-hidden"
          role="region"
          aria-label={t('scrollingTestimonials')}
        >
          <TestimonialsColumn testimonials={firstColumn} duration={25} />
          <TestimonialsColumn
            testimonials={secondColumn}
            className="hidden md:block"
            duration={30}
          />
          <TestimonialsColumn
            testimonials={thirdColumn}
            className="hidden lg:block"
            duration={27}
          />
        </div>
      </motion.div>
    </section>
  );
}
