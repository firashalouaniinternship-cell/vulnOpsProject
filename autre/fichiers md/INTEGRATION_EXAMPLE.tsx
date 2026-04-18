/**
 * Exemple d'intégration du AutoScannerButton dans AnalysisPage
 * Montre comment utiliser le système auto-sélection dans le code existant
 */

import React, { useState } from 'react';
import AutoScannerButton from './AutoScannerButton';

interface Repository {
  name: string;
  full_name: string;
  clone_url: string;
  owner: {
    login: string;
  };
}

interface AnalysisPageProps {
  repository?: Repository;
}

/**
 * Exemple d'utilisation du composant AutoScannerButton
 * dans une page d'analyse existante
 */
export function AnalysisPageExample({ repository }: AnalysisPageProps) {
  const [selectedScanners, setSelectedScanners] = useState<string[]>([]);
  const [autoScanResults, setAutoScanResults] = useState(null);
  
  if (!repository) {
    return <div>Repository not loaded</div>;
  }
  
  return (
    <div className="analysis-page">
      <h1>Code Analysis: {repository.full_name}</h1>
      
      {/* Existing scanner selection UI */}
      <div className="scanner-selection-section">
        <h2>Security Scanners</h2>
        
        {/* NEW: Auto-scanner buttons */}
        <div className="auto-scanner-section">
          <h3>🤖 Automatic Scanner Selection</h3>
          <p className=\"description\">\n            Let AI automatically choose the best scanners for your project:\n          </p>\n          \n          <div className=\"button-group\">\n            {/* Button 1: Just recommend scanners */}\n            <AutoScannerButton\n              repoFullName={repository.full_name}\n              cloneUrl={repository.clone_url}\n              repoName={repository.name}\n              repoOwner={repository.owner.login}\n              variant=\"recommend\"\n              onAutoSelect={(scanners) => {\n                setSelectedScanners(scanners);\n                console.log('Recommended scanners:', scanners);\n              }}\n              className=\"button-recommend\"\n            />\n            \n            {/* Button 2: Auto-detect and launch scans */}\n            <AutoScannerButton\n              repoFullName={repository.full_name}\n              cloneUrl={repository.clone_url}\n              repoName={repository.name}\n              repoOwner={repository.owner.login}\n              variant=\"scan\"\n              onAutoScan={(results) => {\n                setAutoScanResults(results);\n                console.log('Auto-scan results:', results);\n              }}\n              className=\"button-scan\"\n            />\n          </div>\n        </div>\n        \n        {/* Manual scanner selection (existing UI) */}\n        <div className=\"manual-scanner-section\">\n          <h3>📋 Manual Scanner Selection</h3>\n          <p className=\"description\">\n            Or select scanners manually:\n          </p>\n          \n          <div className=\"scanner-buttons\">\n            {/* Your existing scanner buttons */}\n            <button className=\"scanner-button bandit\">🐍 Bandit (Python)</button>\n            <button className=\"scanner-button eslint\">📝 ESLint (JS/TS)</button>\n            <button className=\"scanner-button sonarcloud\">☁️ SonarCloud</button>\n            {/* ... rest of your scanners */}\n          </div>\n        </div>\n      </div>\n      \n      {/* Display auto-selected scanners */}\n      {selectedScanners.length > 0 && (\n        <div className=\"results-section\">\n          <h2>Auto-Selected Scanners</h2>\n          <div className=\"scanners-list\">\n            {selectedScanners.map(scanner => (\n              <div key={scanner} className=\"scanner-item\">\n                ✓ {scanner.toUpperCase()}\n              </div>\n            ))}\n          </div>\n        </div>\n      )}\n      \n      {/* Display auto-scan results */}\n      {autoScanResults && (\n        <div className=\"results-section\">\n          <h2>Scan Results</h2>\n          <div className=\"scan-results-summary\">\n            <p>Total Scans: {autoScanResults.total_scans}</p>\n            {autoScanResults.scan_results?.map((result: any) => (\n              <div key={result.scanner} className={`scan-result ${result.status}`}>\n                <h4>{result.scanner}</h4>\n                <p>Status: {result.status}</p>\n                {result.metrics && (\n                  <ul>\n                    <li>High: {result.metrics.high_count}</li>\n                    <li>Medium: {result.metrics.medium_count}</li>\n                    <li>Low: {result.metrics.low_count}</li>\n                  </ul>\n                )}\n              </div>\n            ))}\n          </div>\n        </div>\n      )}\n      \n      <style>{`\n        .analysis-page {\n          padding: 20px;\n          max-width: 1200px;\n          margin: 0 auto;\n        }\n        \n        .scanner-selection-section {\n          margin: 30px 0;\n        }\n        \n        .scanner-selection-section h2 {\n          font-size: 24px;\n          margin-bottom: 20px;\n          color: #333;\n        }\n        \n        .auto-scanner-section {\n          background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);\n          padding: 20px;\n          border-radius: 8px;\n          border-left: 4px solid #667eea;\n          margin-bottom: 20px;\n        }\n        \n        .auto-scanner-section h3 {\n          margin-top: 0;\n          color: #667eea;\n        }\n        \n        .auto-scanner-section .description {\n          color: #666;\n          font-size: 14px;\n          margin-bottom: 15px;\n        }\n        \n        .button-group {\n          display: flex;\n          gap: 12px;\n          flex-wrap: wrap;\n        }\n        \n        .manual-scanner-section {\n          margin-top: 30px;\n        }\n        \n        .manual-scanner-section h3 {\n          color: #333;\n        }\n        \n        .scanner-buttons {\n          display: flex;\n          gap: 10px;\n          flex-wrap: wrap;\n        }\n        \n        .scanner-button {\n          padding: 10px 16px;\n          border: 1px solid #ddd;\n          border-radius: 6px;\n          background-color: white;\n          cursor: pointer;\n          font-size: 14px;\n          transition: all 0.3s ease;\n        }\n        \n        .scanner-button:hover {\n          border-color: #667eea;\n          background-color: #f0f0f0;\n        }\n        \n        .results-section {\n          margin-top: 30px;\n          padding: 20px;\n          background-color: #f9f9f9;\n          border-radius: 8px;\n          border: 1px solid #eee;\n        }\n        \n        .results-section h2 {\n          margin-top: 0;\n          color: #333;\n        }\n        \n        .scanners-list {\n          display: flex;\n          gap: 8px;\n          flex-wrap: wrap;\n        }\n        \n        .scanner-item {\n          padding: 8px 12px;\n          background-color: #e8f5e9;\n          color: #2e7d32;\n          border-radius: 4px;\n          font-size: 13px;\n          font-weight: 600;\n        }\n        \n        .scan-results-summary {\n          display: flex;\n          flex-direction: column;\n          gap: 12px;\n        }\n        \n        .scan-result {\n          padding: 12px;\n          border-left: 4px solid #ddd;\n          background-color: white;\n          border-radius: 4px;\n        }\n        \n        .scan-result.completed {\n          border-left-color: #4caf50;\n          background-color: #f1f8f5;\n        }\n        \n        .scan-result.failed {\n          border-left-color: #f44336;\n          background-color: #fef5f5;\n        }\n        \n        .scan-result h4 {\n          margin: 0 0 6px 0;\n          color: #333;\n        }\n        \n        .scan-result ul {\n          margin: 8px 0 0 0;\n          padding-left: 20px;\n          font-size: 13px;\n        }\n      `}</style>\n    </div>\n  );\n}\n\nexport default AnalysisPageExample;
