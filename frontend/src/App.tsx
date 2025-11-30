import { BrowserRouter as Router, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Methodology from './pages/Methodology';
import AgentsLayout from './pages/AgentsLayout';
import AgentsHome from './pages/AgentsHome';
import RoadmapDetail from './pages/RoadmapDetail';
import ProfilePage from './pages/ProfilePage';
import Pricing from './pages/Pricing';
import PageTransition from './components/PageTransition';

const MarketingLayout = ({ children }: { children: React.ReactNode }) => (
  <div className="min-h-screen bg-background text-foreground font-sans selection:bg-sage-200 selection:text-foreground flex flex-col">
    <Navbar />
    <main className="flex-grow">
      {children}
    </main>
    <Footer />
  </div>
);

const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <PageTransition>
            <MarketingLayout><Home /></MarketingLayout>
          </PageTransition>
        } />
        <Route path="/methodology" element={
          <PageTransition>
            <MarketingLayout><Methodology /></MarketingLayout>
          </PageTransition>
        } />
        <Route path="/pricing" element={
          <PageTransition>
            <MarketingLayout><Pricing /></MarketingLayout>
          </PageTransition>
        } />

        <Route path="/agents" element={<AgentsLayout />}>
          <Route index element={<Navigate to="/agents/home" replace />} />
          <Route path="home" element={
            <PageTransition>
              <AgentsHome />
            </PageTransition>
          } />
          <Route path="home/:roadmapId" element={
            <PageTransition>
              <RoadmapDetail />
            </PageTransition>
          } />
          <Route path="profile" element={
            <PageTransition>
              <ProfilePage />
            </PageTransition>
          } />
        </Route>
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  return (
    <Router>
      <AnimatedRoutes />
    </Router>
  );
}

export default App;
