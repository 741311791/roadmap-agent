import React from 'react';
import { useNavigate } from 'react-router-dom';
import MyRoadmaps from '../components/MyRoadmaps';

const AgentsHome: React.FC = () => {
    const navigate = useNavigate();

    const handleSelectRoadmap = (id: number) => {
        // For now, always navigate to the demo roadmap
        // In the future, this would use the actual ID: navigate(`/agents/home/${id}`);
        console.log(`Selected roadmap ${id}, navigating to demo...`);
        navigate('/agents/home/demo');
    };

    return (
        <MyRoadmaps onSelectRoadmap={handleSelectRoadmap} />
    );
};

export default AgentsHome;
