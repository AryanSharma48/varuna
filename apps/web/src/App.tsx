import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LandingPage } from './components/LandingPage';
import { InvestigationWorkspace } from './components/InvestigationWorkspace';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing Page with the two clear entry options */}
        <Route path="/" element={<LandingPage />} />

        {/* Dedicated Subroutes */}
        <Route path="/investigation/:id/overview" element={<InvestigationWorkspace />} />
        <Route path="/investigation/:id/satellite" element={<InvestigationWorkspace />} />
        <Route path="/investigation/:id/origin" element={<InvestigationWorkspace />} />
        <Route path="/investigation/:id/ais" element={<InvestigationWorkspace />} />
        <Route path="/investigation/:id/attribution" element={<InvestigationWorkspace />} />
        <Route path="/investigation/:id/forecast" element={<InvestigationWorkspace />} />

        {/* Fallback to root or default overview */}
        <Route path="/investigation/:id" element={<Navigate to="overview" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
