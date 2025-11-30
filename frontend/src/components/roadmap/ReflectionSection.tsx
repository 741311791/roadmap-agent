import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Lightbulb, ChevronDown, ChevronUp, Trash2, Edit2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';

// --- Types ---
interface Reflection {
    id: string;
    title: string;        // LLM 总结的标题 (暂时用时间戳模拟)
    content: string;      // 用户输入的完整内容
    createdAt: Date;
    updatedAt?: Date;
}

interface ReflectionSectionProps {
    conceptId: string;
}

const ReflectionSection: React.FC<ReflectionSectionProps> = ({ conceptId }) => {
    // State
    const [reflections, setReflections] = useState<Reflection[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isFocused, setIsFocused] = useState(false);
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

    // Handlers
    const handleSave = () => {
        if (!inputValue.trim()) return;

        const newReflection: Reflection = {
            id: Date.now().toString(),
            title: `心得 - ${new Date().toLocaleString('zh-CN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            })}`, // Mock: 实际应由 LLM 总结
            content: inputValue,
            createdAt: new Date(),
        };

        setReflections([newReflection, ...reflections]);
        setInputValue('');
        setIsFocused(false);
    };

    const handleDelete = (id: string) => {
        setReflections(reflections.filter(r => r.id !== id));
        expandedIds.delete(id);
        setExpandedIds(new Set(expandedIds));
    };

    const toggleExpand = (id: string) => {
        const newExpanded = new Set(expandedIds);
        if (newExpanded.has(id)) {
            newExpanded.delete(id);
        } else {
            newExpanded.add(id);
        }
        setExpandedIds(newExpanded);
    };

    return (
        <div className="mt-16 pt-12 border-t border-stone-200">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-amber-50 rounded-lg">
                    <Lightbulb size={20} className="text-amber-600" />
                </div>
                <h2 className="text-2xl font-serif font-bold text-stone-800">
                    学习心得
                </h2>
                <span className="text-sm text-stone-400 ml-2">
                    ({reflections.length})
                </span>
            </div>

            {/* 极简输入框 */}
            <motion.div
                className={cn(
                    "mb-8 border border-stone-200 rounded-xl bg-white transition-all",
                    isFocused ? "shadow-md ring-2 ring-sage-500/20" : "shadow-sm"
                )}
                animate={{
                    padding: isFocused ? '16px' : '12px',
                }}
                transition={{ duration: 0.2 }}
            >
                <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={(e) => {
                        // 延迟 blur，让按钮点击事件先触发
                        setTimeout(() => {
                            if (!inputValue.trim()) {
                                setIsFocused(false);
                            }
                        }, 150);
                    }}
                    placeholder="Write a reflection..."
                    className={cn(
                        "w-full bg-transparent text-stone-700 placeholder:text-stone-400",
                        "focus:outline-none resize-none transition-all",
                        "text-sm leading-relaxed"
                    )}
                    style={{
                        height: isFocused ? '120px' : '40px',
                        transition: 'height 0.2s ease-out'
                    }}
                />

                <AnimatePresence>
                    {isFocused && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.15 }}
                            className="flex justify-end mt-3 pt-3 border-t border-stone-100"
                        >
                            <Button
                                onClick={handleSave}
                                disabled={!inputValue.trim()}
                                className="bg-sage-600 hover:bg-sage-700 text-white px-6 h-9 text-sm rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Save
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* 心得列表 */}
            <div className="space-y-3">
                {reflections.length === 0 ? (
                    <div className="text-center py-12 bg-stone-50/50 rounded-xl border border-stone-100 border-dashed">
                        <div className="w-14 h-14 bg-white rounded-full shadow-sm flex items-center justify-center mx-auto mb-3">
                            <Lightbulb size={24} className="text-stone-300" />
                        </div>
                        <p className="text-stone-500 text-sm">
                            还没有记录心得，开始写下你的学习感悟吧
                        </p>
                    </div>
                ) : (
                    reflections.map((reflection) => {
                        const isExpanded = expandedIds.has(reflection.id);

                        return (
                            <motion.div
                                key={reflection.id}
                                layout
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="group bg-white border border-stone-200 rounded-xl hover:shadow-md transition-all overflow-hidden"
                            >
                                {/* 标题栏（可点击展开） */}
                                <button
                                    onClick={() => toggleExpand(reflection.id)}
                                    className="w-full px-5 py-4 flex items-center justify-between hover:bg-stone-50/50 transition-colors text-left"
                                >
                                    <div className="flex items-center gap-3 flex-1">
                                        <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                        <span className="font-medium text-stone-800 text-sm">
                                            {reflection.title}
                                        </span>
                                        <span className="text-xs text-stone-400">
                                            {reflection.createdAt.toLocaleDateString('zh-CN')}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        {/* 操作按钮 - 悬停时显示 */}
                                        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 mr-2">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    // TODO: 实现编辑功能
                                                }}
                                                className="p-1.5 hover:bg-stone-100 rounded-md text-stone-400 hover:text-stone-600 transition-colors"
                                                title="编辑"
                                            >
                                                <Edit2 size={14} />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDelete(reflection.id);
                                                }}
                                                className="p-1.5 hover:bg-red-50 rounded-md text-stone-400 hover:text-red-500 transition-colors"
                                                title="删除"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>

                                        {/* 展开/收起图标 */}
                                        {isExpanded ? (
                                            <ChevronUp size={16} className="text-stone-400" />
                                        ) : (
                                            <ChevronDown size={16} className="text-stone-400" />
                                        )}
                                    </div>
                                </button>

                                {/* 内容区（展开时显示） */}
                                <AnimatePresence>
                                    {isExpanded && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            transition={{ duration: 0.2 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="px-5 pb-4 pt-2 border-t border-stone-100">
                                                <p className="text-sm text-stone-600 leading-relaxed whitespace-pre-wrap">
                                                    {reflection.content}
                                                </p>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        );
                    })
                )}
            </div>
        </div>
    );
};

export default ReflectionSection;
