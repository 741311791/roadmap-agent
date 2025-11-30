import React, { useState } from 'react';
import {
    Wand2,
    PlayCircle,
    FileText,
    Code,
    Check,
    ChevronDown,
    ShieldCheck,
    Briefcase,
    Layers,
    Plus,
    Trash2,
    Languages,
    BrainCircuit
} from 'lucide-react';
import { Button } from '../components/ui/Button';

// --- Mock Data & Constants ---

const INDUSTRIES = [
    "Technology",
    "Finance",
    "Healthcare",
    "Education",
    "Design",
    "Student",
    "Other"
];

const ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Product Manager",
    "Data Scientist",
    "Designer",
    "Founder",
    "Student",
    "Other"
];

const TECH_STACK_OPTIONS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js",
    "SQL", "AWS", "Docker", "Go", "Rust", "Java", "C++"
];

const LANGUAGES = [
    "English", "Chinese (Simplified)", "Chinese (Traditional)", "Spanish", "French", "German", "Japanese", "Korean"
];

type Proficiency = 'beginner' | 'intermediate' | 'expert';

interface TechStackItem {
    id: string;
    tech: string;
    proficiency: Proficiency;
}

// --- Helper Components ---

const SectionTitle = ({ children, icon: Icon }: { children: React.ReactNode, icon?: any }) => (
    <div className="flex items-center gap-2 mb-6">
        {Icon && <Icon className="w-5 h-5 text-sage-600" />}
        <h2 className="text-xl font-serif font-bold text-foreground">{children}</h2>
    </div>
);

const CustomSelect = ({
    label,
    value,
    onChange,
    options,
    placeholder = "Select option"
}: {
    label?: string,
    value: string,
    onChange: (val: string) => void,
    options: string[],
    placeholder?: string
}) => (
    <div className="flex-1 w-full">
        {label && (
            <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                {label}
            </label>
        )}
        <div className="relative group">
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full appearance-none bg-background border border-border rounded-xl px-4 py-3 pr-10 text-foreground font-medium focus:outline-none focus:ring-2 focus:ring-sage-500/20 focus:border-sage-500 transition-all hover:border-sage-300 cursor-pointer"
            >
                <option value="" disabled>{placeholder}</option>
                {options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none group-hover:text-foreground transition-colors" />
        </div>
    </div>
);

const ToggleSwitch = ({ checked, onChange }: { checked: boolean, onChange: (checked: boolean) => void }) => (
    <button
        onClick={() => onChange(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-sage-500/20 ${checked ? 'bg-sage-600' : 'bg-muted'
            }`}
    >
        <span
            className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'
                }`}
        />
    </button>
);

const ContentPreferenceCard = ({
    icon: Icon,
    label,
    selected,
    onClick
}: {
    icon: any,
    label: string,
    selected: boolean,
    onClick: () => void
}) => (
    <div
        onClick={onClick}
        className={`
            relative flex flex-col items-center justify-center gap-3 p-6 rounded-2xl border cursor-pointer transition-all duration-200
            ${selected
                ? 'bg-sage-50 border-sage-500 shadow-sm'
                : 'bg-card border-border hover:border-sage-300 hover:bg-sage-50/30'
            }
        `}
    >
        {selected && (
            <div className="absolute top-3 right-3 w-5 h-5 bg-sage-600 rounded-full flex items-center justify-center">
                <Check className="w-3 h-3 text-white" />
            </div>
        )}
        <div className={`p-3 rounded-full ${selected ? 'bg-sage-100 text-sage-700' : 'bg-muted text-muted-foreground'}`}>
            <Icon size={24} />
        </div>
        <span className={`font-medium ${selected ? 'text-sage-900' : 'text-foreground/70'}`}>{label}</span>
    </div>
);

const ProficiencySlider = ({ value, onChange }: { value: Proficiency, onChange: (val: Proficiency) => void }) => {
    const steps: Proficiency[] = ['beginner', 'intermediate', 'expert'];
    const currentIndex = steps.indexOf(value);

    return (
        <div className="w-full px-1">
            <div className="flex justify-between mb-2">
                {steps.map((step, idx) => (
                    <span
                        key={step}
                        className={`text-[10px] uppercase font-bold tracking-wider cursor-pointer transition-colors ${idx === currentIndex ? 'text-sage-700' : 'text-muted-foreground/50'
                            }`}
                        onClick={() => onChange(step)}
                    >
                        {step}
                    </span>
                ))}
            </div>
            <div className="relative h-1.5 bg-muted rounded-full">
                <div
                    className="absolute h-full bg-sage-500 rounded-full transition-all duration-300 ease-out"
                    style={{
                        width: `${(currentIndex / (steps.length - 1)) * 100}%`,
                        left: 0
                    }}
                />
                {steps.map((step, idx) => (
                    <div
                        key={step}
                        className={`absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full border-2 transition-colors cursor-pointer ${idx <= currentIndex
                                ? 'bg-white border-sage-500'
                                : 'bg-muted border-transparent'
                            }`}
                        style={{ left: `${(idx / (steps.length - 1)) * 100}%`, transform: 'translate(-50%, -50%)' }}
                        onClick={() => onChange(step)}
                    />
                ))}
            </div>
        </div>
    );
};

// --- Main Component ---

const ProfilePage: React.FC = () => {
    // State
    const [privacyConsent, setPrivacyConsent] = useState(true);
    const [industry, setIndustry] = useState("");
    const [role, setRole] = useState("");

    // Tech Stack State
    const [techStack, setTechStack] = useState<TechStackItem[]>([
        { id: '1', tech: 'Python', proficiency: 'intermediate' },
        { id: '2', tech: 'JavaScript', proficiency: 'beginner' }
    ]);

    // Language State
    const [primaryLanguage, setPrimaryLanguage] = useState("English");
    const [secondaryLanguage, setSecondaryLanguage] = useState("");

    const [studyHours, setStudyHours] = useState(10);
    const [contentPref, setContentPref] = useState("video");

    // Handlers
    const addTechStackItem = () => {
        const newId = Math.random().toString(36).substr(2, 9);
        setTechStack([...techStack, { id: newId, tech: '', proficiency: 'beginner' }]);
    };

    const removeTechStackItem = (id: string) => {
        setTechStack(techStack.filter(item => item.id !== id));
    };

    const updateTechStackItem = (id: string, field: keyof TechStackItem, value: any) => {
        setTechStack(techStack.map(item =>
            item.id === id ? { ...item, [field]: value } : item
        ));
    };

    const handleAssessmentStart = (tech: string) => {
        console.log(`Starting AI Assessment for ${tech}...`);
        // Placeholder for future implementation
    };

    return (
        <div className="min-h-full py-12 px-6 flex justify-center">
            <div className="w-full max-w-3xl space-y-12">

                {/* Header */}
                <div className="text-center space-y-4 mb-12">
                    <h1 className="text-4xl font-serif font-bold text-foreground">Your Profile</h1>
                    <p className="text-muted-foreground text-lg max-w-xl mx-auto">
                        Customize your learning experience. We use this to tailor your roadmap and recommendations.
                    </p>
                </div>

                {/* 1. Privacy Context */}
                <div className="bg-card rounded-2xl border border-border p-6 flex items-center justify-between shadow-sm">
                    <div className="flex items-center gap-4">
                        <div className="p-2.5 bg-sage-100 text-sage-700 rounded-xl">
                            <ShieldCheck size={20} />
                        </div>
                        <div>
                            <h3 className="font-medium text-foreground">AI Personalization</h3>
                            <p className="text-sm text-muted-foreground">Allow AI to analyze your progress for better recommendations.</p>
                        </div>
                    </div>
                    <ToggleSwitch checked={privacyConsent} onChange={setPrivacyConsent} />
                </div>

                {/* 2. Professional Identity */}
                <section>
                    <SectionTitle icon={Briefcase}>Professional Background</SectionTitle>
                    <div className="flex flex-col md:flex-row gap-6">
                        <CustomSelect
                            label="Industry"
                            value={industry}
                            onChange={setIndustry}
                            options={INDUSTRIES}
                        />
                        <CustomSelect
                            label="Current Role"
                            value={role}
                            onChange={setRole}
                            options={ROLES}
                        />
                    </div>
                </section>

                {/* 3. Technical DNA (Refactored) */}
                <section>
                    <div className="flex items-center justify-between mb-6">
                        <SectionTitle icon={Code}>Current Tech Stack</SectionTitle>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={addTechStackItem}
                            className="text-sage-700 border-sage-200 hover:bg-sage-50"
                        >
                            <Plus size={16} className="mr-2" /> Add Technology
                        </Button>
                    </div>

                    <div className="space-y-4">
                        {techStack.map((item) => (
                            <div key={item.id} className="bg-card rounded-2xl border border-border p-5 shadow-sm transition-all hover:border-sage-300">
                                <div className="flex flex-col md:flex-row gap-6 items-start md:items-center">

                                    {/* Tech Select */}
                                    <div className="w-full md:w-1/3">
                                        <CustomSelect
                                            value={item.tech}
                                            onChange={(val) => updateTechStackItem(item.id, 'tech', val)}
                                            options={TECH_STACK_OPTIONS}
                                            placeholder="Select Tech"
                                        />
                                    </div>

                                    {/* Proficiency Slider */}
                                    <div className="flex-1 w-full pt-2">
                                        <ProficiencySlider
                                            value={item.proficiency}
                                            onChange={(val) => updateTechStackItem(item.id, 'proficiency', val)}
                                        />
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-3 w-full md:w-auto justify-end">
                                        {item.tech && (
                                            <button
                                                onClick={() => handleAssessmentStart(item.tech)}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-sage-50 text-sage-700 text-xs font-medium rounded-lg hover:bg-sage-100 transition-colors border border-sage-200"
                                                title="Take Skill Assessment"
                                            >
                                                <BrainCircuit size={14} />
                                                <span>Assess</span>
                                            </button>
                                        )}
                                        <button
                                            onClick={() => removeTechStackItem(item.id)}
                                            className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                            title="Remove"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}

                        {techStack.length === 0 && (
                            <div className="text-center py-8 bg-muted/30 rounded-2xl border border-dashed border-border">
                                <p className="text-muted-foreground text-sm">No technologies added yet.</p>
                                <Button variant="link" onClick={addTechStackItem} className="text-sage-600">
                                    Add your first technology
                                </Button>
                            </div>
                        )}
                    </div>
                </section>

                {/* 4. Language Preferences (New) */}
                <section>
                    <SectionTitle icon={Languages}>Language Preferences</SectionTitle>
                    <div className="bg-card rounded-2xl border border-border p-6 shadow-sm">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <CustomSelect
                                label="Primary Language"
                                value={primaryLanguage}
                                onChange={setPrimaryLanguage}
                                options={LANGUAGES}
                            />
                            <CustomSelect
                                label="Secondary Language"
                                value={secondaryLanguage}
                                onChange={setSecondaryLanguage}
                                options={["None", ...LANGUAGES]}
                            />
                        </div>
                    </div>
                </section>

                {/* 5. Learning Habits */}
                <section>
                    <SectionTitle icon={Layers}>Learning Habits</SectionTitle>
                    <div className="space-y-8">

                        {/* Time Slider */}
                        <div className="bg-card rounded-2xl border border-border p-6 shadow-sm">
                            <div className="flex justify-between items-center mb-4">
                                <label className="text-sm font-medium text-foreground">Weekly Commitment</label>
                                <span className="text-sage-700 font-bold font-serif text-lg">{studyHours} hours</span>
                            </div>
                            <input
                                type="range"
                                min="5"
                                max="40"
                                step="5"
                                value={studyHours}
                                onChange={(e) => setStudyHours(parseInt(e.target.value))}
                                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-sage-600"
                            />
                            <div className="flex justify-between text-xs text-muted-foreground mt-2">
                                <span>Casual (5h)</span>
                                <span>Intense (40h)</span>
                            </div>
                        </div>

                        {/* Content Preferences */}
                        <div>
                            <p className="text-sm font-medium text-foreground mb-4">Preferred Learning Style</p>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <ContentPreferenceCard
                                    icon={PlayCircle}
                                    label="Video First"
                                    selected={contentPref === 'video'}
                                    onClick={() => setContentPref('video')}
                                />
                                <ContentPreferenceCard
                                    icon={FileText}
                                    label="Documentation"
                                    selected={contentPref === 'text'}
                                    onClick={() => setContentPref('text')}
                                />
                                <ContentPreferenceCard
                                    icon={Code}
                                    label="Project Based"
                                    selected={contentPref === 'project'}
                                    onClick={() => setContentPref('project')}
                                />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Save Action */}
                <div className="flex justify-end pt-6 border-t border-border">
                    <Button size="lg" className="bg-sage-900 text-sage-50 hover:bg-sage-800 px-8">
                        Save Profile
                    </Button>
                </div>

            </div>
        </div>
    );
};

export default ProfilePage;
