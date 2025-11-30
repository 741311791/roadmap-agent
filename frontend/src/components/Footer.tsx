import React from 'react';

const Footer: React.FC = () => {
    return (
        <footer className="py-12 px-6 bg-card border-t border-border">
            <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-xs">
                        M
                    </div>
                    <span className="font-serif font-bold text-lg tracking-tight">Muset</span>
                </div>

                <div className="text-sm text-muted-foreground">
                    © 2025 Muset AI. All rights reserved.
                </div>

                <div className="flex gap-6 text-sm font-medium text-muted-foreground">
                    <a href="#" className="hover:text-foreground">Twitter</a>
                    <a href="#" className="hover:text-foreground">GitHub</a>
                    <a href="#" className="hover:text-foreground">Discord</a>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
