import React from 'react';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/Card';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { Progress } from './ui/Progress';
import { Separator } from './ui/Separator';
import { Plus, Heart, Copy, ArrowRight, BookOpen, Sparkles } from 'lucide-react';

interface MyRoadmapsProps {
    onSelectRoadmap: (id: number) => void;
}

const MyRoadmaps: React.FC<MyRoadmapsProps> = ({ onSelectRoadmap }) => {
    // Mock Data
    const myRoadmaps = [
        { id: 1, title: "Python Mastery", progress: 65, last_active: "2h ago", status: "active" },
        { id: 2, title: "React Visualized", progress: 10, last_active: "1d ago", status: "paused" }
    ];

    const communityRoadmaps = [
        { id: 101, title: "System Design 101", author: "Alice", likes: 340, clones: 120, tags: ["Backend", "Arch"] },
        { id: 102, title: "Rust for JS Devs", author: "Bob", likes: 120, clones: 45, tags: ["Rust", "Hard"] }
    ];

    return (
        <div className="max-w-7xl mx-auto py-12 px-6 space-y-12">

            {/* SECTION 1: PERSONAL LIBRARY */}
            <section className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-3xl font-serif font-bold text-foreground">Your Learning Path</h2>
                    <Button className="bg-charcoal text-white hover:bg-charcoal/90">
                        <Plus className="mr-2 h-4 w-4" /> Create New Roadmap
                    </Button>
                </div>

                {myRoadmaps.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {myRoadmaps.map((roadmap) => (
                            <Card key={roadmap.id} className="border-stone-200 shadow-sm hover:shadow-md transition-shadow bg-white">
                                <CardHeader className="pb-3">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="p-2 bg-sage-50 rounded-lg">
                                            <BookOpen className="h-6 w-6 text-sage-600" />
                                        </div>
                                        <Badge variant="secondary" className="bg-sage-50 text-sage-700 hover:bg-sage-100">
                                            {roadmap.status === 'active' ? 'In Progress' : 'Paused'}
                                        </Badge>
                                    </div>
                                    <CardTitle className="font-serif text-xl font-bold text-charcoal">
                                        {roadmap.title}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pb-3">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-muted-foreground">Progress</span>
                                            <span className="font-medium text-sage-700">{roadmap.progress}%</span>
                                        </div>
                                        <Progress value={roadmap.progress} className="h-2 bg-stone-100" />
                                    </div>
                                </CardContent>
                                <CardFooter className="pt-3 border-t border-stone-100 flex justify-between items-center">
                                    <span className="text-xs text-muted-foreground">Last studied {roadmap.last_active}</span>
                                    <Button
                                        variant="ghost"
                                        className="text-sage-700 hover:text-sage-800 hover:bg-sage-50 p-0 h-auto font-medium"
                                        onClick={() => onSelectRoadmap(roadmap.id)}
                                    >
                                        Continue <ArrowRight className="ml-1 h-4 w-4" />
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <Card className="border-dashed border-2 border-stone-200 bg-stone-50/50">
                        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm mb-4">
                                <Sparkles className="h-8 w-8 text-sage-400" />
                            </div>
                            <h3 className="font-serif text-xl font-semibold mb-2">Start your first journey</h3>
                            <p className="text-muted-foreground max-w-md mb-6">
                                Create a custom roadmap or explore community curated paths to begin your learning adventure.
                            </p>
                            <Button>Create Roadmap</Button>
                        </CardContent>
                    </Card>
                )}
            </section>

            <Separator className="bg-stone-200" />

            {/* SECTION 2: COMMUNITY / DISCOVERY */}
            <section className="space-y-6">
                <div className="flex items-center gap-3">
                    <h2 className="text-2xl font-serif font-medium text-foreground">Curated by Community</h2>
                    <Badge variant="outline" className="text-xs font-normal text-muted-foreground border-stone-200">
                        Popular this week
                    </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {communityRoadmaps.map((roadmap) => (
                        <Card key={roadmap.id} className="border-stone-100 bg-stone-50/50 hover:bg-white hover:shadow-sm transition-all group cursor-pointer">
                            <div className="h-32 bg-gradient-to-br from-stone-100 to-stone-200 relative overflow-hidden rounded-t-xl group-hover:from-sage-50 group-hover:to-sage-100 transition-colors">
                                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#444_1px,transparent_1px)] [background-size:16px_16px]"></div>
                                <div className="absolute bottom-3 left-3">
                                    <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm text-xs font-bold text-stone-600 border border-stone-100">
                                        {roadmap.author[0]}
                                    </div>
                                </div>
                            </div>
                            <CardContent className="pt-4 pb-3">
                                <h3 className="font-medium text-lg text-foreground mb-1 group-hover:text-sage-800 transition-colors">
                                    {roadmap.title}
                                </h3>
                                <p className="text-xs text-muted-foreground mb-3">by {roadmap.author}</p>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    {roadmap.tags.map(tag => (
                                        <span key={tag} className="px-2 py-0.5 bg-white border border-stone-200 rounded text-[10px] text-stone-600 font-medium">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </CardContent>
                            <CardFooter className="pt-0 pb-4 text-muted-foreground text-xs flex gap-4">
                                <span className="flex items-center gap-1 hover:text-red-500 transition-colors">
                                    <Heart className="h-3 w-3" /> {roadmap.likes}
                                </span>
                                <span className="flex items-center gap-1 hover:text-blue-500 transition-colors">
                                    <Copy className="h-3 w-3" /> {roadmap.clones || 0}
                                </span>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            </section>
        </div>
    );
};

export default MyRoadmaps;
