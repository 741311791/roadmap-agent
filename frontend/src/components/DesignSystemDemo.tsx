/**
 * Design System Showcase Component
 * Demonstrates the Editorial Cream & Sage design tokens and patterns
 */

export function DesignSystemDemo() {
    return (
        <div className="min-h-screen bg-background p-8">
            <div className="max-w-4xl mx-auto space-y-12">

                {/* Header */}
                <header className="border-b border-border pb-6">
                    <h1 className="font-serif text-6xl font-semibold text-foreground">
                        Editorial Cream & Sage
                    </h1>
                    <p className="text-muted-foreground mt-2 text-lg">
                        A sophisticated design system for modern web applications
                    </p>
                </header>

                {/* Typography Section */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Typography Hierarchy
                    </h2>
                    <div className="space-y-3">
                        <h1 className="font-serif text-5xl">Heading 1 - Serif</h1>
                        <h2 className="font-serif text-4xl">Heading 2 - Serif</h2>
                        <h3 className="font-serif text-3xl">Heading 3 - Serif</h3>
                        <p className="text-foreground font-sans">
                            Body text uses Inter, a clean sans-serif font for optimal readability.
                            This ensures a perfect balance between the authoritative serif headings
                            and approachable body content.
                        </p>
                        <p className="text-muted-foreground">
                            Muted text for secondary information or subtle emphasis.
                        </p>
                    </div>
                </section>

                {/* Color Palette */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Color Palette
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="space-y-2">
                            <div className="h-24 bg-background border-2 border-border rounded-lg"></div>
                            <p className="text-sm font-medium">Background</p>
                            <code className="text-xs text-muted-foreground">bg-background</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-24 bg-foreground rounded-lg"></div>
                            <p className="text-sm font-medium">Foreground</p>
                            <code className="text-xs text-muted-foreground">bg-foreground</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-24 bg-sage rounded-lg"></div>
                            <p className="text-sm font-medium">Sage (Accent)</p>
                            <code className="text-xs text-muted-foreground">bg-sage</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-24 bg-muted rounded-lg"></div>
                            <p className="text-sm font-medium">Muted</p>
                            <code className="text-xs text-muted-foreground">bg-muted</code>
                        </div>
                    </div>
                </section>

                {/* Sage Variations */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Sage Green Spectrum
                    </h2>
                    <div className="grid grid-cols-5 gap-2">
                        <div className="space-y-2">
                            <div className="h-16 bg-sage-100 rounded-md"></div>
                            <code className="text-xs">sage-100</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-16 bg-sage-300 rounded-md"></div>
                            <code className="text-xs">sage-300</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-16 bg-sage rounded-md"></div>
                            <code className="text-xs">sage (500)</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-16 bg-sage-700 rounded-md"></div>
                            <code className="text-xs">sage-700</code>
                        </div>
                        <div className="space-y-2">
                            <div className="h-16 bg-sage-900 rounded-md"></div>
                            <code className="text-xs">sage-900</code>
                        </div>
                    </div>
                </section>

                {/* Button Variants */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Button Patterns
                    </h2>
                    <div className="flex flex-wrap gap-4">
                        <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-md font-medium transition-colors">
                            Primary Button
                        </button>
                        <button className="bg-sage text-white hover:bg-sage/90 px-6 py-3 rounded-md font-medium transition-colors">
                            Sage Accent Button
                        </button>
                        <button className="bg-transparent border border-border hover:bg-muted px-6 py-3 rounded-md font-medium transition-colors">
                            Ghost Button
                        </button>
                        <button className="bg-muted text-foreground hover:bg-muted/80 px-6 py-3 rounded-md font-medium transition-colors">
                            Secondary Button
                        </button>
                    </div>
                </section>

                {/* Glass Panel Components */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Glass Panel Components
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="glass-panel p-6">
                            <h3 className="font-serif text-2xl font-semibold mb-3">
                                Editorial Card
                            </h3>
                            <p className="text-muted-foreground mb-4">
                                Clean, sophisticated cards with subtle backdrop blur create
                                a sense of depth and hierarchy.
                            </p>
                            <button className="bg-sage text-white hover:bg-sage/90 px-4 py-2 rounded-md text-sm font-medium transition-colors">
                                Learn More
                            </button>
                        </div>

                        <div className="bg-card border border-border p-6 rounded-lg">
                            <h3 className="font-serif text-2xl font-semibold mb-3">
                                Standard Card
                            </h3>
                            <p className="text-muted-foreground mb-4">
                                Traditional cards with solid backgrounds maintain the warm,
                                paper-like aesthetic.
                            </p>
                            <button className="bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-md text-sm font-medium transition-colors">
                                Get Started
                            </button>
                        </div>
                    </div>
                </section>

                {/* Form Elements */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Form Elements
                    </h2>
                    <div className="space-y-4 max-w-md">
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                Glass Input
                            </label>
                            <input
                                type="text"
                                className="glass-input w-full"
                                placeholder="Enter your name"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                Standard Input
                            </label>
                            <input
                                type="email"
                                className="bg-muted border border-input focus:border-primary/50 focus:ring-2 focus:ring-ring/20 transition-all outline-none rounded-md px-4 py-2 w-full"
                                placeholder="your@email.com"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                Textarea
                            </label>
                            <textarea
                                className="glass-input w-full resize-none"
                                rows={4}
                                placeholder="Your message..."
                            />
                        </div>
                    </div>
                </section>

                {/* Sage Accent Usage */}
                <section className="space-y-6">
                    <h2 className="font-serif text-4xl font-semibold text-foreground">
                        Sage Accent in Context
                    </h2>
                    <div className="glass-panel p-8">
                        <p className="text-xl text-foreground leading-relaxed">
                            Welcome to{' '}
                            <span className="text-sage font-semibold">Concrete Path</span>, where
                            we believe in{' '}
                            <span className="text-sage">strategic design</span> and{' '}
                            <span className="text-sage">thoughtful execution</span>. Our approach
                            combines editorial sophistication with modern web aesthetics.
                        </p>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-border pt-8 text-center">
                    <p className="text-muted-foreground">
                        Editorial Cream & Sage Design System · Sophisticated · Warm · Timeless
                    </p>
                </footer>

            </div>
        </div>
    );
}
