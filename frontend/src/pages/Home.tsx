import React from 'react';
import Hero from '../components/Hero';
import InputSection from '../components/InputSection';
import Architecture from '../components/Architecture';
import Agents from '../components/Agents';
import ConceptView from '../components/ConceptView';

const Home: React.FC = () => {
    return (
        <>
            <Hero />
            <InputSection />
            <Architecture />
            <Agents />
            <ConceptView />
        </>
    );
};

export default Home;
