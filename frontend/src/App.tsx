import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import ProjectsPage from './pages/ProjectsPage';
import AnalysisPage from './pages/AnalysisPage';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/projects" element={<Navigate to="/MesProjects" replace />} />
        <Route path="/Dashboard" element={<ProjectsPage />} />
        <Route path="/MesProjects" element={<ProjectsPage />} />
        <Route path="/ProjetExterne" element={<ProjectsPage />} />
        <Route path="/analysis/:owner/:repo" element={<AnalysisPage />} />
      </Routes>
    </Router>
  );
};

export default App;
