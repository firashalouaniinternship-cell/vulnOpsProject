/**
 * Exemple d'intégration du composant AutoScannerSimplified
 * Affiche UNIQUEMENT le scanner recommandé par l'LLM
 * Remplace complètement l'interface manuelle
 */

import React, { useState } from 'react';
import AutoScannerSimplified from './AutoScannerSimplified';

interface Repository {
  name: string;
  full_name: string;
  clone_url: string;
  owner: {
    login: string;
  };
}

interface SimplifiedAnalysisPageProps {
  repository?: Repository;
}

/**
 * Version simplifiée de la page d'analyse
 * Montre UNIQUEMENT le scanner choisi automatiquement
 */
export function SimplifiedAnalysisPage({ repository }: SimplifiedAnalysisPageProps) {
  const [selectedScanner, setSelectedScanner] = useState<string | null>(null);
  const [scanComplete, setScanComplete] = useState(false);
  
  if (!repository) {
    return <div className="page">Repository not loaded</div>;
  }
  
  return (
    <div className="simplified-analysis-page">
      <header className="page-header">
        <h1>{repository.full_name}</h1>
        <p className="subtitle">Python repository - Security Analysis</p>
      </header>
      
      <main className="page-content">
        {/* ONLY THIS COMPONENT - Auto-selected scanner button */}
        <section className="scanner-section">
          <div className="section-title">
            <span className="badge">🤖 AI-Powered</span>
            <h2>Security Scan</h2>
          </div>
          
          <AutoScannerSimplified
            repoFullName={repository.full_name}
            cloneUrl={repository.clone_url}
            repoName={repository.name}
            repoOwner={repository.owner.login}
            onScannerSelected={(scanner) => {
              console.log('Selected scanner:', scanner);
              setSelectedScanner(scanner);
            }}
            onAnalysisComplete={(data) => {
              console.log('Scan completed:', data);
              setScanComplete(true);
            }}
          />
          
          {selectedScanner && (
            <p className="info-text">
              ✅ System automatically selected <strong>{selectedScanner.toUpperCase()}</strong> as the best scanner for this project.
            </p>
          )}
        </section>
        
        {/* Optional: Show historical scans */}
        {scanComplete && (
          <section className="history-section">
            <h2>Recent Scans</h2>
            <div className="scan-list">
              <div className="scan-item completed">
                <div className="scan-header">
                  <span className="scan-name">Auto Scan</span>
                  <span className="scan-date">Just now</span>
                </div>
                <div className="scan-summary">
                  <span className="issues high">4 High</span>
                  <span className="issues medium">8 Medium</span>
                  <span className="issues low">12 Low</span>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
      
      <style>{`
        .simplified-analysis-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
          padding: 20px;
        }
        
        .page-header {
          max-width: 800px;
          margin: 0 auto 40px;
          text-align: center;
        }
        
        .page-header h1 {
          margin: 0 0 8px 0;
          font-size: 32px;
          color: #2c3e50;
          font-weight: 700;
        }
        
        .page-header .subtitle {
          margin: 0;
          font-size: 14px;
          color: #7f8c8d;
        }
        
        .page-content {
          max-width: 800px;
          margin: 0 auto;
        }
        
        .scanner-section {
          background: white;
          border-radius: 12px;
          padding: 32px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
          margin-bottom: 24px;
        }
        
        .section-title {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 24px;
        }
        
        .badge {
          display: inline-block;
          font-size: 12px;
          padding: 6px 10px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border-radius: 20px;
          font-weight: 600;
        }
        
        .section-title h2 {
          margin: 0;
          font-size: 24px;
          color: #2c3e50;
          font-weight: 600;
        }
        
        .info-text {
          margin-top: 20px;
          padding: 12px;
          background-color: #e8f5e9;
          border-left: 4px solid #4caf50;
          border-radius: 4px;
          font-size: 14px;
          color: #2e7d32;
        }
        
        .history-section {
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        }
        
        .history-section h2 {
          margin: 0 0 16px 0;
          font-size: 18px;
          color: #2c3e50;
        }
        
        .scan-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .scan-item {
          padding: 16px;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          background-color: #fafafa;
          transition: all 0.3s ease;
        }
        
        .scan-item:hover {
          border-color: #667eea;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }
        
        .scan-item.completed {
          border-left: 4px solid #4caf50;
        }
        
        .scan-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        
        .scan-name {
          font-weight: 600;
          color: #333;
        }
        
        .scan-date {
          font-size: 12px;
          color: #999;
        }
        
        .scan-summary {
          display: flex;
          gap: 12px;
          font-size: 13px;
          font-weight: 500;
        }
        
        .issues {
          padding: 4px 8px;
          border-radius: 3px;
        }
        
        .issues.high {
          background-color: #ffebee;
          color: #c62828;
        }
        
        .issues.medium {
          background-color: #fff3e0;
          color: #e65100;
        }
        
        .issues.low {
          background-color: #e8f5e9;
          color: #2e7d32;
        }
        
        @media (max-width: 600px) {
          .page-header h1 {
            font-size: 24px;
          }
          
          .scanner-section {
            padding: 20px;
          }
          
          .section-title {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
}

export default SimplifiedAnalysisPage;
