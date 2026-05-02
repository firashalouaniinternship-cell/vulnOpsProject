/**
 * Composant Auto-Scanner Simplifié
 * Affiche UNIQUEMENT le scanner auto-sélectionné par l'LLM
 * Pas d'autres boutons de scanner
 */

import React, { useState, useEffect } from 'react';
import { Globe, Shield, Box, Check, Loader2, Settings } from 'lucide-react';
import useAutoScannerSelection from '../hooks/useAutoScannerSelection';
import api, { endpoints } from '../api/client';

interface AutoScannerSimplifiedProps {
  repoFullName: string;
  cloneUrl: string;
  repoName: string;
  repoOwner: string;
  onScannerSelected?: (scanner: string) => void;
  onAnalysisComplete?: (data: any) => void;
  onScanStart?: () => void;
  onScanStatusChange?: (type: 'sast' | 'sca' | 'container' | 'dast', isScanning: boolean) => void;
  className?: string;
  customToken?: string;
  repoLanguage?: string;
  selectedPaths?: string[];
  branch?: string;
  scanMode?: 'fast' | 'standard' | 'deep';
}

interface ScannerInfo {
  name: string;
  icon: string;
  color: string;
  description: string;
}

const SCANNER_INFO: Record<string, ScannerInfo> = {
  bandit: {
    name: 'Bandit',
    icon: '🐍',
    color: '#3776ab',
    description: 'Python Security Scanner'
  },
  eslint: {
    name: 'ESLint',
    icon: '📝',
    color: '#4b32c3',
    description: 'JavaScript/TypeScript Linter'
  },
  sonarcloud: {
    name: 'SonarCloud',
    icon: '☁️',
    color: '#1e90ff',
    description: 'Multi-Language Code Quality'
  },
  semgrep: {
    name: 'Semgrep',
    icon: '🔍',
    color: '#ffa500',
    description: 'Pattern-Based Analysis'
  },
  cppcheck: {
    name: 'Cppcheck',
    icon: '⚙️',
    color: '#00a8ff',
    description: 'C/C++ Static Analysis'
  },
  gosec: {
    name: 'Gosec',
    icon: '🔐',
    color: '#00add8',
    description: 'Go Security Scanner'
  },
  psalm: {
    name: 'Psalm',
    icon: '✨',
    color: '#7367f0',
    description: 'PHP Static Analysis'
  },
  brakeman: {
    name: 'Brakeman',
    icon: '🛡️',
    color: '#cc342d',
    description: 'Ruby on Rails Security'
  },
  clippy: {
    name: 'Clippy',
    icon: '🦀',
    color: '#ce422b',
    description: 'Rust Linter'
  },
  detekt: {
    name: 'Detekt',
    icon: '🎯',
    color: '#7f52ff',
    description: 'Kotlin Static Analysis'
  },
  zap: {
    name: 'OWASP ZAP',
    icon: '🌐',
    color: '#ef4444',
    description: 'Dynamic Application Security Testing'
  },
};

export function AutoScannerSimplified({
  repoFullName,
  cloneUrl,
  repoName,
  repoOwner,
  onScannerSelected,
  onAnalysisComplete,
  onScanStart,
  onScanStatusChange,
  className = '',
  customToken,
  repoLanguage,
  selectedPaths = [],
  branch,
  scanMode = 'standard',
}: AutoScannerSimplifiedProps) {
  const { selectScanners, autoScan, loading, error, progress } = useAutoScannerSelection();

  const [selectedScanner, setSelectedScanner] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [scaScanning, setScaScanning] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [activeScanMode, setActiveScanMode] = useState<'fast' | 'standard' | 'deep'>(scanMode as 'fast' | 'standard' | 'deep');
  const [enabledScanners, setEnabledScanners] = useState({
    sast: false,
    sca: false,
    container: false,
    dast: false
  });
  const [containerImage, setContainerImage] = useState('');

  const SCAN_MODES: { id: 'fast' | 'standard' | 'deep'; label: string; desc: string; color: string }[] = [
    { id: 'fast',     label: '⚡ Fast',     desc: 'Semgrep uniquement, < 2 min',            color: '#10b981' },
    { id: 'standard', label: '🔍 Standard', desc: 'LLM choisit parmi Semgrep / SonarCloud', color: '#6366f1' },
    { id: 'deep',     label: '🧠 Deep',     desc: 'LLM choisit parmi tous les scanners',     color: '#f59e0b' },
  ];



  // Auto-detect scanner on mount
  useEffect(() => {
    detectAndSelectScanner();
  }, [repoFullName, branch]);

  const detectAndSelectScanner = async () => {
    try {
      const result = await selectScanners(repoFullName, cloneUrl, repoName, repoOwner, customToken, branch);

      if (result.success && result.suggested_scanners.length > 0) {
        // Take the first (best) scanner
        const bestScanner = result.suggested_scanners[0];
        setSelectedScanner(bestScanner);
        setAnalysis(result);

        // Only call onScannerSelected if we don't already have one selected or if it's the first detection
        // to avoid reverting manual selections (like Trivy)
        if (!selectedScanner) {
          onScannerSelected?.(bestScanner);
        }
      }
    } catch (err) {
      console.error('Auto-detection failed:', err);
    }
  };

  const handleLaunchScan = async () => {
    setScanning(true);
    setLocalError(null);
    onScanStart?.();

    let finalAnalysis = analysis;
    let parentScanId: number | null = null;

    try {
    // Phase 1: SAST, SCA & Container
    if (enabledScanners.sast || enabledScanners.sca || enabledScanners.container) {
      let phaseNames = [];
      if (enabledScanners.sast) phaseNames.push('SAST');
      if (enabledScanners.sca) phaseNames.push('SCA');
      if (enabledScanners.container) phaseNames.push('Container');

      const phaseName = phaseNames.join(' & ');
      setCurrentPhase(phaseName);
      
      if (enabledScanners.sast) onScanStatusChange?.('sast', true);
      if (enabledScanners.sca) onScanStatusChange?.('sca', true);
      if (enabledScanners.container) onScanStatusChange?.('container', true);

      try {
        const result = await autoScan(
          repoFullName,
          cloneUrl,
          repoName,
          repoOwner,
          customToken,
          enabledScanners.sca,
          enabledScanners.sast,
          enabledScanners.container,
          containerImage,
          selectedPaths,
          branch,
          activeScanMode
        );

          if (result && (result as any).scan_results && (result as any).scan_results.length > 0) {
            parentScanId = (result as any).scan_results[0].scan_id;
          }

          finalAnalysis = {
            ...finalAnalysis,
            ...result,
            analysis: (result as any).analysis || finalAnalysis?.analysis,
          };

          setAnalysis(finalAnalysis);
          onAnalysisComplete?.(result);
          if (enabledScanners.sast) onScanStatusChange?.('sast', false);
          if (enabledScanners.sca) onScanStatusChange?.('sca', false);
          if (enabledScanners.container) onScanStatusChange?.('container', false);
        } catch (err: any) {
          console.error('SAST/SCA/Container phase failed:', err);
          setLocalError(`Scan Phase Failed: ${err.message || 'Unknown error'}`);
          if (enabledScanners.sast) onScanStatusChange?.('sast', false);
          if (enabledScanners.sca) onScanStatusChange?.('sca', false);
          if (enabledScanners.container) onScanStatusChange?.('container', false);
          // On continue si possible pour le DAST
        }

      }

      // Phase 2: DAST (Automated Build & Scan)
      if (enabledScanners.dast) {
        setCurrentPhase('DAST');
        onScanStatusChange?.('dast', true);
        try {
          const res = await api.post(endpoints.scanner.dastAutoScan, {
            clone_url: cloneUrl,
            repo_full_name: repoFullName,
            repo_owner: repoOwner,
            repo_name: repoName,
            custom_token: customToken,
            branch: branch,
            parent_scan_id: parentScanId
          });

          // Combine DAST results with previous ones
          finalAnalysis = {
            ...finalAnalysis,
            scan_results: [
              ...(finalAnalysis?.scan_results || []),
              {
                scanner: 'zap',
                status: 'COMPLETED',
                metrics: res.data.metrics,
                scan_id: res.data.scan_id
              }
            ]
          };

          setAnalysis(finalAnalysis);
          onAnalysisComplete?.(res.data);
          onScanStatusChange?.('dast', false);
        } catch (err: any) {
          console.error('DAST phase failed:', err);
          setLocalError(prev => prev ? `${prev} | DAST Failed` : 'DAST Failed');
          onScanStatusChange?.('dast', false);
        }

      }

      setShowDetails(true);
    } catch (err) {
      console.error('Auto-scan execution error:', err);
    } finally {
      setScanning(false);
      setCurrentPhase(null);
    }
  };

  const toggleAll = (val: boolean) => {
    setEnabledScanners({
      sast: val,
      sca: val,
      container: val,
      dast: val
    });
  };

  const isContainerReady = !enabledScanners.container || containerImage.trim() !== '';
  const isAnyEnabled = (enabledScanners.sast || enabledScanners.sca || enabledScanners.container || enabledScanners.dast) && isContainerReady;
  const isAllEnabled = enabledScanners.sast && enabledScanners.sca && enabledScanners.container && enabledScanners.dast && containerImage.trim() !== '';


  if (!selectedScanner) {
    return (
      <div className={`auto-scanner-simplified loading ${className}`}>
        <div className="loading-spinner">
          <span className="spinner"></span>
          <p>Detecting best scanner...</p>
        </div>
      </div>
    );
  }

  const scannerInfo = SCANNER_INFO[selectedScanner] || {
    name: selectedScanner.toUpperCase(),
    icon: '🔧',
    color: '#666',
    description: 'Security Scanner'
  };

  return (
    <div className={`auto-scanner-simplified ${className}`}>
      <div className="scanner-selection-area">
        {/* Header row: label + détails toggle */}
        <div className="scanner-header">
          <p className="auto-detected">🤖 Auto-Detected Scanner</p>
          {analysis && (
            <button
              className="info-toggle"
              onClick={() => setShowDetails(!showDetails)}
              title="Voir les détails de détection"
            >
              {showDetails ? '▼' : '▶'} Détails
            </button>
          )}
        </div>

        {/* Collapsible details — shown inline below the header */}
        {analysis && showDetails && (
          <div className="analysis-details">
            <div className="detail-row">
              <span className="label">Langages détectés :</span>
              <span className="value">
                {analysis.analysis?.languages?.join(', ') || 'N/A'}
              </span>
            </div>

            {analysis.analysis?.frameworks &&
              Object.keys(analysis.analysis.frameworks).length > 0 && (
                <div className="detail-row">
                  <span className="label">Frameworks :</span>
                  <span className="value">
                    {Object.entries(analysis.analysis.frameworks)
                      .map(([lang, fw]: [string, any]) => `${lang}: ${fw.join(', ')}`)
                      .join(' | ')}
                  </span>
                </div>
              )}

            <div className="detail-row">
              <span className="label">Confiance :</span>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{ width: `${(analysis.confidence || 0) * 100}%`, backgroundColor: scannerInfo.color }}
                />
                <span className="confidence-text">
                  {((analysis.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {analysis.reasoning && (
              <div className="detail-row">
                <span className="label">Pourquoi ce scanner ?</span>
                <p className="reasoning">{analysis.reasoning}</p>
              </div>
            )}
          </div>
        )}

        {/* Scan Mode Selector */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '12px',
          marginBottom: '8px'
        }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '10px' }}>
            Mode de scan
          </span>
          <div style={{ display: 'flex', gap: '6px' }}>
            {SCAN_MODES.map(mode => (
              <button
                key={mode.id}
                onClick={() => setActiveScanMode(mode.id)}
                title={mode.desc}
                style={{
                  flex: 1,
                  padding: '8px 4px',
                  border: '1px solid',
                  borderColor: activeScanMode === mode.id ? mode.color : 'var(--border)',
                  borderRadius: '6px',
                  background: activeScanMode === mode.id ? `${mode.color}18` : 'transparent',
                  color: activeScanMode === mode.id ? mode.color : 'var(--text-dim)',
                  fontSize: '11px',
                  fontWeight: activeScanMode === mode.id ? 700 : 400,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  textAlign: 'center',
                  lineHeight: 1.4,
                }}
              >
                {mode.label}
                <div style={{ fontSize: '9px', opacity: 0.7, marginTop: '2px', fontWeight: 400, color: 'inherit' }}>
                  {mode.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Scan Type Selection Area */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border)',
          borderRadius: '10px',
          padding: '12px',
          marginBottom: '8px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Scope de l'analyse
            </span>
            <button
              onClick={() => toggleAll(!isAllEnabled)}
              style={{ background: 'none', border: 'none', color: 'var(--primary)', fontSize: '11px', cursor: 'pointer', fontWeight: 600 }}
            >
              {isAllEnabled ? 'Désélectionner tout' : 'Tout sélectionner'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { id: 'sast', label: 'SAST (Static Analysis)', icon: <Shield size={14} />, desc: `Analysis with ${scannerInfo.name}` },
              { id: 'sca', label: 'SCA (Dependency Scan)', icon: <Box size={14} />, desc: 'Detect vulnerable libs with Trivy' },
              { id: 'container', label: 'Container Scanning', icon: <Shield size={14} />, desc: 'Scan with Trivy' },
              { id: 'dast', label: 'DAST (Dynamic Analysis)', icon: <Globe size={14} />, desc: 'Real-time test (requires Docker)' },
            ].map(type => (
              <label
                key={type.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 10px',
                  background: (enabledScanners as any)[type.id] ? 'rgba(99, 102, 241, 0.05)' : 'transparent',
                  border: '1px solid',
                  borderColor: (enabledScanners as any)[type.id] ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <input
                  type="checkbox"
                  checked={(enabledScanners as any)[type.id]}
                  onChange={() => setEnabledScanners(prev => ({ ...prev, [type.id]: !(prev as any)[type.id] }))}
                  style={{ cursor: 'pointer' }}
                />
                <div style={{ color: (enabledScanners as any)[type.id] ? 'var(--primary)' : 'var(--text-dim)' }}>
                  {type.icon}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: (enabledScanners as any)[type.id] ? 'white' : 'var(--text-dim)' }}>
                    {type.label}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-dim)', opacity: 0.7 }}>
                    {type.desc}
                  </span>
                </div>
                {(enabledScanners as any)[type.id] && <Check size={14} color="var(--primary)" style={{ marginLeft: 'auto' }} />}
              </label>
            ))}

            {enabledScanners.container && (
              <div style={{ 
                marginTop: '4px', 
                padding: '10px', 
                background: 'rgba(255, 255, 255, 0.02)', 
                border: '1px dashed var(--border)', 
                borderRadius: '6px' 
              }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'block', marginBottom: '6px' }}>
                  Image Container à scanner (ex: myapp:latest)
                </span>
                <input
                  type="text"
                  value={containerImage}
                  onChange={(e) => setContainerImage(e.target.value)}
                  placeholder="image-name:tag"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: 'rgba(0, 0, 0, 0.2)',
                    border: '1px solid var(--border)',
                    borderRadius: '4px',
                    color: 'white',
                    fontSize: '12px',
                    outline: 'none'
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Action Button */}
        <button
          className="scanner-button main-button"
          onClick={() => handleLaunchScan()}
          disabled={loading || scanning || !isAnyEnabled}
          style={{
            borderColor: isAnyEnabled ? (scanning ? 'var(--border)' : scannerInfo.color) : 'var(--border)',
            background: isAnyEnabled ? 'white' : 'rgba(255,255,255,0.02)',
            opacity: isAnyEnabled ? 1 : 0.5
          }}
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            background: isAnyEnabled ? (scanning ? 'rgba(0,0,0,0.05)' : `${scannerInfo.color}15`) : 'transparent',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            {scanning ? <Loader2 className="animate-spin" size={20} color="var(--primary)" /> : scannerInfo.icon}
          </div>
          <div className="scanner-text">
             <span className="scanner-name" style={{ color: isAnyEnabled ? '#333' : 'var(--text-dim)' }}>
               {scanning ? 'Analyse en cours...' : `Lancer l'analyse ${selectedPaths.length > 0 ? `(${selectedPaths.length} cibles)` : ''}`}
             </span>
             <span className="scanner-desc">
               {scanning ? (currentPhase ? `Analyse ${currentPhase} en cours...` : 'Analyse en cours...') : 
                selectedPaths.length > 0 ? `Scanner uniquement les ${selectedPaths.length} éléments sélectionnés` : 'Exécuter le scope sélectionné sur tout le projet'}
             </span>
          </div>
        </button>

        {(loading || scanning || scaScanning) && (
          <p className="progress-text">
            {scaScanning ? 'Running SCA analysis...' : progress || 'Processing...'}
          </p>
        )}

        {(error || localError) && (
          <div className="error-alert">
            ❌ Error: {localError || error}
          </div>
        )}

      </div>

      <style>{`
        .auto-scanner-simplified {
          width: 100%;
          max-width: 600px;
        }
        
        .auto-scanner-simplified.loading {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 120px;
        }
        
        .loading-spinner {
          text-align: center;
        }
        
        .spinner {
          display: inline-block;
          width: 20px;
          height: 20px;
          border: 3px solid rgba(102, 126, 234, 0.3);
          border-top-color: #667eea;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin-bottom: 10px;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .scanner-selection-area {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .scanner-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }

        .auto-detected {
          margin: 0;
          font-size: 11px;
          font-weight: 600;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .scanner-button {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 16px;
          background: white;
          border: 2px solid #ddd;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s ease;
          font-family: inherit;
          text-align: left;
        }
        
        .scanner-button.main-button {
          border-width: 2px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .scanner-button:not(:disabled):hover {
          border-color: currentColor;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
          transform: translateY(-2px);
        }
        
        .scanner-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        
        .scanner-button .spinner {
          width: 16px;
          height: 16px;
          margin-left: auto;
        }
        
        .scanner-icon {
          font-size: 28px;
          min-width: 40px;
          text-align: center;
        }
        
        .scanner-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        
        .scanner-name {
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        
        .scanner-desc {
          font-size: 12px;
          color: #999;
        }
        
        .progress-text {
          margin: 0;
          font-size: 12px;
          color: #667eea;
          font-weight: 500;
          text-align: center;
        }
        
        .error-alert {
          padding: 10px 12px;
          background-color: #ffebee;
          border: 1px solid #ffcdd2;
          border-radius: 4px;
          color: #c62828;
          font-size: 13px;
        }
        
        .analysis-info {
          margin-top: 8px;
        }
        
        .info-toggle {
          padding: 4px 8px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid var(--border);
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          font-weight: 600;
          color: var(--text-dim);
          white-space: nowrap;
          transition: all 0.2s ease;
          font-family: inherit;
        }

        .info-toggle:hover {
          background: rgba(255, 255, 255, 0.1);
          color: white;
        }

        .analysis-details {
          padding: 10px 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border);
          border-radius: 6px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .detail-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .label {
          font-size: 10px;
          font-weight: 600;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }

        .value {
          font-size: 12px;
          color: var(--text-bright, white);
        }

        .confidence-bar {
          position: relative;
          width: 100%;
          height: 20px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 4px;
          overflow: hidden;
        }

        .confidence-fill {
          height: 100%;
          transition: width 0.3s ease;
          opacity: 0.85;
        }

        .confidence-text {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          font-size: 11px;
          font-weight: 600;
          color: white;
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
        }

        .reasoning {
          margin: 0;
          font-size: 11px;
          color: var(--text-dim);
          font-style: italic;
          padding: 6px 8px;
          border-radius: 3px;
          border-left: 2px solid var(--primary);
          background: rgba(99, 102, 241, 0.06);
        }
        

      `}</style>
    </div>
  );
}

export default AutoScannerSimplified;
