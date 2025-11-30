import React from 'react';
import { Menu } from 'lucide-react';
import { Link } from 'react-router-dom';

const Navbar: React.FC = () => {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4 flex justify-between items-center bg-background/80 backdrop-blur-md">
            <Link to="/" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground font-serif font-bold text-lg">
                    M
                </div>
                <span className="font-serif font-bold text-xl tracking-tight">Muset</span>
            </Link>

            <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
                <Link to="/methodology" className="hover:text-foreground transition-colors">Methodology</Link>
                <Link to="/agents" className="hover:text-foreground transition-colors">Agents</Link>
                <Link to="/pricing" className="hover:text-foreground transition-colors">Pricing</Link>
            </div>

            <div className="flex items-center gap-4">
                <button className="md:hidden text-foreground">
                    <Menu size={24} />
                </button>
                <button className="hidden md:block px-5 py-2 bg-primary text-primary-foreground rounded-full text-sm font-medium hover:bg-primary/90 transition-colors">
                    Start Learning
                </button>
            </div>
        </nav>
    );
};

export default Navbar;
