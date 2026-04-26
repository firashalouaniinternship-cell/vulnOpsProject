import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ChevronLeft, Loader2, Info, AlertTriangle, ShieldCheck, FileText, ExternalLink, Trash2, RotateCcw, GitBranch } from 'lucide-react';
import api, { endpoints } from '../api/client';
import FileTree from '../components/FileTree';
import ScanResults, { type Vulnerability } from '../components/ScanResults';
import AutoScannerSimplified from '../components/AutoScannerSimplified';
import DastPanel from '../components/DastPanel';
import ConsolidatedView from '../components/ConsolidatedView';

type ScannerType = 'bandit' | 'sonarcloud' | 'eslint' | 'semgrep' | 'cppcheck' | 'gosec' | 'psalm' | 'brakeman' | 'clippy' | 'detekt' | 'trivy' | 'zap';

const AnalysisPage: React.FC = () => {
  const { owner, repo } = useParams<{ owner: string; repo: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const repoLanguage = location.state?.language || 'Inconnu';
  const customToken = location.state?.customToken;
  const cloneUrl = location.state?.cloneUrl || `https://github.com/${owner}/${repo}.git`;

  const [tree, setTree] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState<Vulnerability[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [currentScanFeatures, setCurrentScanFeatures] = useState({ run_sast: true, run_sca: false, run_container: false, run_dast: false });
  const [history, setHistory] = useState<any[]>([]);
  const [selectedScanner, setSelectedScanner] = useState<ScannerType>('sonarcloud');
  const [showZeroModal, setShowZeroModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'sast' | 'sca' | 'container' | 'dast' | 'report'>('sast');
  const [isSastScanning, setIsSastScanning] = useState(false);
  const [isScaScanning, setIsScaScanning] = useState(false);
  const [isDastScanning, setIsDastScanning] = useState(false);
  const [scanDate, setScanDate] = useState<string | null>(null);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const hasResultsRef = useRef(false);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [isTreeLoading, setIsTreeLoading] = useState(false);

  const [deleteModalConfig, setDeleteModalConfig] = useState<{
    isOpen: boolean;
    type: 'single' | 'all';
    scanId?: number;
  }>({ isOpen: false, type: 'single' });

  const handleDeleteScan = (e: React.MouseEvent, scanId: number) => {
    e.stopPropagation();
    setDeleteModalConfig({ isOpen: true, type: 'single', scanId });
  };

  const handleDeleteAllHistory = () => {
    setDeleteModalConfig({ isOpen: true, type: 'all' });
  };

  const executeDeletion = async () => {
    const { type, scanId } = deleteModalConfig;

    if (type === 'single' && scanId) {
      setIsDeleting(scanId);
      try {
        await api.delete(`${endpoints.scanner.detail(scanId)}delete/`);
        setHistory(prev => prev.filter(s => s.id !== scanId));
        if (scanResults && scanResults.length > 0 && history.find(s => s.id === scanId)) {
          // Clean search if needed
        }
      } catch (err) {
        console.error('Erreur lors de la suppression du scan:', err);
        alert("Erreur lors de la suppression");
      } finally {
        setIsDeleting(null);
        setDeleteModalConfig({ ...deleteModalConfig, isOpen: false });
      }
    } else if (type === 'all') {
      try {
        await api.delete(`${endpoints.scanner.history(owner || '', repo || '')}delete-all/`);
        setHistory([]);
        setScanResults([]);
        setMetrics(null);
      } catch (err) {
        console.error('Erreur lors de la suppression de l\'historique:', err);
        alert("Erreur lors de la suppression de l'historique");
      } finally {
        setDeleteModalConfig({ ...deleteModalConfig, isOpen: false });
      }
    }
  };

  const scannerName = selectedScanner === 'sonarcloud' ? 'SonarCloud' :
    selectedScanner === 'eslint' ? 'ESLint' :
      selectedScanner === 'cppcheck' ? 'Cppcheck' :
        selectedScanner === 'gosec' ? 'Gosec' :
          selectedScanner === 'psalm' ? 'Psalm' :
            selectedScanner === 'brakeman' ? 'Brakeman' :
              selectedScanner === 'clippy' ? 'Clippy' :
                selectedScanner === 'detekt' ? 'Detekt' :
                  selectedScanner === 'semgrep' ? 'Semgrep' :
                    selectedScanner === 'trivy' ? 'Trivy (Container)' :
                      selectedScanner === 'zap' ? 'ZAP (DAST)' : 'Bandit';

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (!owner || !repo) return;

        const [treeRes, historyRes, branchesRes] = await Promise.all([
          api.get(endpoints.projects.tree(owner, repo), { 
            params: { 
              ...(customToken ? { custom_token: customToken } : {}),
              branch: selectedBranch 
            } 
          }),
          api.get(endpoints.scanner.history(owner, repo), { params: customToken ? { custom_token: customToken } : undefined }),
          api.get(endpoints.projects.branches(owner, repo), { params: customToken ? { custom_token: customToken } : undefined })
        ]);

        setTree(treeRes.data.tree);
        setHistory(historyRes.data);
        setBranches(branchesRes.data);
        
        // Si la branche par défaut n'est pas main/master, on pourrait vouloir la setter ici
        // Mais pour l'instant on garde 'main' ou celle choisie.
      } catch (err) {
        console.error('Erreur lors du chargement des données:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [owner, repo]);

  const handleBranchChange = async (branchName: string) => {
    setSelectedBranch(branchName);
    setIsTreeLoading(true);
    try {
      const res = await api.get(endpoints.projects.tree(owner || '', repo || ''), {
        params: {
          ...(customToken ? { custom_token: customToken } : {}),
          branch: branchName
        }
      });
      setTree(res.data.tree);
      setSelectedPaths(new Set()); // Reset selection when branch changes
    } catch (err) {
      console.error('Erreur changement branche:', err);
    } finally {
      setIsTreeLoading(false);
    }
  };



  const loadPastScan = async (scanId: number, append: boolean = false) => {
    setScanning(true);
    try {
      // Préparer l'interface pour le type de scan attendu (si on peut le déduire de l'historique ou du trigger)
      // Mais ici on attend la réponse pour être sûr
      const response = await api.get(endpoints.scanner.detail(scanId), { params: customToken ? { custom_token: customToken } : undefined });

      const scannerType = response.data.scanner_type as ScannerType;

      // Toujours mettre à jour l'interface avec le nouveau scan
      const newVulns = response.data.vulnerabilities || [];
      const newMetrics = response.data.metrics || { critical_count: 0, high_count: 0, medium_count: 0, low_count: 0 };

      if (append) {
        setScanResults(prev => {
          // Avoid duplicates
          const existingIds = new Set(prev.map(v => v.id));
          const uniqueNewVulns = newVulns.filter((v: any) => !existingIds.has(v.id));
          return [...prev, ...uniqueNewVulns];
        });
        setMetrics(prev => {
          if (!prev) return newMetrics;
          return {
            critical_count: (prev.critical_count || 0) + (newMetrics.critical_count || 0),
            high_count: prev.high_count + newMetrics.high_count,
            medium_count: prev.medium_count + newMetrics.medium_count,
            low_count: prev.low_count + newMetrics.low_count,
          };
        });
      } else {
        setScanResults(newVulns);
        setMetrics(newMetrics);
      }

      setSelectedScanner(scannerType);
      setScanDate(response.data.started_at);

      if (!append) {
        setCurrentScanFeatures({
          run_sast: response.data.run_sast !== false,
          run_sca: response.data.run_sca === true,
          run_container: response.data.run_container === true,
          run_dast: response.data.run_dast === true
        });
      } else {
        // En mode append (multi-scan progressif), on met à jour les features avec le OU logique
        setCurrentScanFeatures(prev => ({
          run_sast: prev.run_sast || response.data.run_sast !== false,
          run_sca: prev.run_sca || response.data.run_sca === true,
          run_container: prev.run_container || response.data.run_container === true,
          run_dast: prev.run_dast || response.data.run_dast === true
        }));
      }

      // Changer d'onglet intelligemment
      const { run_sast, run_sca, run_container, run_dast } = response.data;
      if (scannerType === 'zap' || (run_dast && !run_sast && !run_sca && !run_container)) {
        setActiveTab('dast');
      } else if (scannerType === 'trivy' || (run_container && !run_sast && !run_sca)) {
        setActiveTab('container');
      } else if (run_sca && !run_sast) {
        setActiveTab('sca');
      } else if (run_sast !== false) {
        setActiveTab('sast');
      }

      // Si 0 faille, afficher le modal de succès
      if (!response.data.vulnerabilities || response.data.vulnerabilities.length === 0) {
        setShowZeroModal(true);
      }
    } catch (err) {
      console.error('Erreur lors du chargement du scan passé:', err);
    } finally {
      setScanning(false);
    }
  };

  const getScannerDisplayName = (type: string) => {
    switch (type) {
      case 'sonarcloud': return 'SonarCloud';
      case 'eslint': return 'ESLint';
      case 'semgrep': return 'Semgrep';
      case 'cppcheck': return 'Cppcheck';
      case 'gosec': return 'Gosec';
      case 'psalm': return 'Psalm';
      case 'brakeman': return 'Brakeman';
      case 'clippy': return 'Clippy';
      case 'detekt': return 'Detekt';
      case 'bandit': return 'Bandit';
      case 'trivy': return 'Trivy (Container)';
      case 'zap': return 'OWASP ZAP';
      default: return type;
    }
  };

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(location.state?.fromDashboard ? '/Dashboard' : '/MesProjects')}
            className="flex items-center gap-1"
            style={{ color: 'var(--text-dim)', fontSize: '14px' }}
          >
            <ChevronLeft size={16} />
            {location.state?.fromDashboard ? 'Dashboard' : 'Mes Projets'}
          </button>
          <div style={{ width: '1px', height: '20px', background: 'var(--border)' }}></div>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold' }}>{owner} / {repo}</h2>
          
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.03)', padding: '4px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <GitBranch size={14} color="var(--primary)" />
            <select 
              value={selectedBranch}
              onChange={(e) => handleBranchChange(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'white',
                fontSize: '13px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
                padding: '2px 0'
              }}
            >
              {branches.length > 0 ? (
                branches.map(b => (
                  <option key={b.name} value={b.name} style={{ background: '#0f172a' }}>{b.name}</option>
                ))
              ) : (
                <option value={selectedBranch}>{selectedBranch}</option>
              )}
            </select>
          </div>

          <span className="badge badge-low" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)', border: '1px solid var(--border)' }}>
            {repoLanguage}
          </span>
        </div>
      </nav>

      <main className="main-content" style={{ padding: '0' }}>
        <div className="analysis-layout" style={{ height: 'calc(100vh - 64px)', padding: '24px' }}>
          {/* Sidebar - Explorateur de fichiers */}
          <div className="sidebar-panel">
            <div className="panel-header flex justify-between items-center">
              <span style={{ fontWeight: 600, fontSize: '14px' }}>Explorateur</span>
              <FileText size={16} color="var(--text-dim)" />
            </div>
            {loading || isTreeLoading ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <Loader2 size={24} className="animate-spin" />
              </div>
            ) : (
              <FileTree
                tree={tree}
                selectedPaths={selectedPaths}
                onSelectionChange={setSelectedPaths}
              />
            )}
            <div className="panel-footer" style={{ padding: '16px', background: 'transparent' }}>
              <AutoScannerSimplified
                repoFullName={`${owner}/${repo}`}
                branch={selectedBranch}
                cloneUrl={cloneUrl}
                repoName={repo || ''}
                repoOwner={owner || ''}
                customToken={customToken}
                repoLanguage={repoLanguage}
                selectedPaths={Array.from(selectedPaths)}
                onScanStart={() => {
                  setScanResults([]);
                  setMetrics(null);
                  hasResultsRef.current = false;
                }}
                onScannerSelected={(scanner) => {
                  if (scanner) setSelectedScanner(scanner as ScannerType);
                }}
                onScanStatusChange={(type, isScanning) => {
                  if (type === 'sast') setIsSastScanning(isScanning);
                  else if (type === 'sca') setIsScaScanning(isScanning);
                  else if (type === 'container') setIsScaScanning(isScanning); // On re-utilise isScaScanning ou on pourrait en créer un autre
                  else if (type === 'dast') setIsDastScanning(isScanning);
                }}
                onAnalysisComplete={async (data) => {
                  try {
                    if (owner && repo) {
                      const historyRes = await api.get(endpoints.scanner.history(owner, repo), { params: customToken ? { custom_token: customToken } : undefined });
                      setHistory(historyRes.data);
                    }

                    // Utilisation d'une ref pour contourner le problème des closures React lors des appels asynchrones
                    const shouldAppend = hasResultsRef.current;
                    hasResultsRef.current = true;

                    if (data && data.scan_results && data.scan_results.length > 0) {
                      const scanInfo = data.scan_results[0];
                      if (scanInfo.scan_id) {
                        await loadPastScan(scanInfo.scan_id, shouldAppend);
                      }
                    } else if (data && data.scan_id) {
                      await loadPastScan(data.scan_id, shouldAppend);
                    }
                  } catch (err) {
                    console.error('Error post-analysis:', err);
                  }
                }}
              />
            </div>
          </div>

          {/* Right Panel - Résultats */}
          <div className="results-panel">
            <div className="panel-header flex justify-between items-center">
              <div className="flex items-center gap-3">
                {scanResults.length > 0 && (
                  <button
                    onClick={() => {
                      setScanResults([]);
                      setMetrics(null);
                      setScanDate(null);
                      setActiveTab('sast');
                    }}
                    className="flex items-center gap-1 hover:text-white transition-colors"
                    style={{
                      color: 'var(--text-dim)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border)',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      marginRight: '8px'
                    }}
                  >
                    <ChevronLeft size={14} /> Retour
                  </button>
                )}
                <span style={{ fontWeight: 600, fontSize: '14px' }}>
                  {scanResults.length > 0 ? `Résultats de l'analyse :` : "Historique des scans"}
                </span>
                {scanResults.length > 0 && (
                  <span className="badge badge-low" style={{ background: 'var(--primary)', color: 'white', marginLeft: '8px' }}>
                    {scanResults.length} issues
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                {scanDate && (
                  <div style={{
                    fontSize: '12px',
                    color: 'var(--text-dim)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 8px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: '6px',
                    border: '1px solid var(--border)'
                  }}>
                    <span style={{ opacity: 0.6 }}>Date du scan:</span>
                    <span style={{ fontWeight: 500, color: 'var(--text-bright)' }}>
                      {new Date(scanDate).toLocaleString('fr-FR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                )}
                {metrics && (
                  <div className="flex gap-4">
                    <div className="flex gap-2 items-center" style={{ borderRight: '1px solid var(--border)', paddingRight: '12px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)' }}>SAST:</span>
                      <div className="flex gap-1.5">
                        {metrics.critical_count > 0 && <span style={{ fontSize: '11px', color: 'var(--critical)', fontWeight: 'bold' }}>{metrics.critical_count}</span>}
                        <span style={{ fontSize: '11px', color: 'var(--high)' }}>{metrics.high_count}</span>
                        <span style={{ fontSize: '11px', color: 'var(--warning)' }}>{metrics.medium_count}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 items-center" style={{ borderRight: '1px solid var(--border)', paddingRight: '12px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)' }}>SCA:</span>
                      <div className="flex gap-1.5">
                        {metrics.sca_critical_count > 0 && <span style={{ fontSize: '11px', color: 'var(--critical)', fontWeight: 'bold' }}>{metrics.sca_critical_count}</span>}
                        <span style={{ fontSize: '11px', color: 'var(--high)' }}>{metrics.sca_high_count}</span>
                        <span style={{ fontSize: '11px', color: 'var(--warning)' }}>{metrics.sca_medium_count}</span>
                      </div>
                    </div>
                    {(metrics.container_high_count > 0 || metrics.container_medium_count > 0) && (
                      <div className="flex gap-2 items-center">
                        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-dim)' }}>CONT:</span>
                        <div className="flex gap-1.5">
                          {metrics.container_critical_count > 0 && <span style={{ fontSize: '11px', color: 'var(--critical)', fontWeight: 'bold' }}>{metrics.container_critical_count}</span>}
                          <span style={{ fontSize: '11px', color: 'var(--high)' }}>{metrics.container_high_count}</span>
                          <span style={{ fontSize: '11px', color: 'var(--warning)' }}>{metrics.container_medium_count}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {scanResults.length > 0 && (
              <div style={{
                display: 'flex',
                padding: '0 16px',
                borderBottom: '1px solid var(--border)',
                background: 'rgba(255,255,255,0.01)'
              }}>
                {currentScanFeatures.run_sast && (
                  <button
                    onClick={() => setActiveTab('sast')}
                    style={{
                      padding: '12px 20px',
                      background: 'none',
                      border: 'none',
                      borderBottom: activeTab === 'sast' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'sast' ? 'white' : 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    🛡️ SAST Analysis
                  </button>
                )}
                {currentScanFeatures.run_sca && (
                  <button
                    onClick={() => setActiveTab('sca')}
                    style={{
                      padding: '12px 20px',
                      background: 'none',
                      border: 'none',
                      borderBottom: activeTab === 'sca' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'sca' ? 'white' : 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    📦 SCA (Dependency-Check)
                  </button>
                )}
                {currentScanFeatures.run_container && (
                  <button
                    onClick={() => setActiveTab('container')}
                    style={{
                      padding: '12px 20px',
                      background: 'none',
                      border: 'none',
                      borderBottom: activeTab === 'container' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'container' ? 'white' : 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    🐳 Container (Trivy)
                  </button>
                )}
                {currentScanFeatures.run_dast && (
                  <button
                    onClick={() => setActiveTab('dast')}
                    style={{
                      padding: '12px 20px',
                      background: 'none',
                      border: 'none',
                      borderBottom: activeTab === 'dast' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'dast' ? 'white' : 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    🌐 DAST (ZAP)
                  </button>
                )}
                {!scanning && (
                  <button
                    onClick={() => setActiveTab('report')}
                    style={{
                      padding: '12px 20px',
                      background: 'none',
                      border: 'none',
                      borderBottom: activeTab === 'report' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'report' ? 'white' : 'var(--text-dim)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    📄 Rapport Final
                  </button>
                )}

              </div>
            )}

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {scanning && scanResults.length === 0 ? (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
                  <Loader2 size={48} className="animate-spin" style={{ marginBottom: '16px' }} />
                  <p>{scannerName} analyse votre code {repoLanguage}...</p>
                  <p style={{ fontSize: '12px', marginTop: '8px' }}>Cela peut prendre quelques secondes.</p>
                </div>
              ) : activeTab === 'dast' && scanResults.filter(v => !!v.is_dast).length === 0 ? (
                <DastPanel
                  repoFullName={`${owner}/${repo}`}
                  repoOwner={owner || ''}
                  repoName={repo || ''}
                  cloneUrl={cloneUrl}
                  customToken={customToken}
                  isRemoteScanning={isDastScanning}
                  onScanComplete={async (data) => {
                    // Refresh history and load result
                    if (owner && repo) {
                      const historyRes = await api.get(endpoints.scanner.history(owner, repo), { params: customToken ? { custom_token: customToken } : undefined });
                      setHistory(historyRes.data);
                    }
                    if (data.scan_id) await loadPastScan(data.scan_id);
                  }}
                />
              ) : activeTab === 'report' ? (
                <ConsolidatedView vulnerabilities={scanResults} />
              ) : scanResults.length > 0 ? (
                <ScanResults
                  vulnerabilities={scanResults.filter(v => {
                    if (activeTab === 'sast') return v.is_sca !== true && v.is_dast !== true && v.is_container !== true;
                    if (activeTab === 'sca') return v.is_sca === true;
                    if (activeTab === 'container') return v.is_container === true;
                    if (activeTab === 'dast') return v.is_dast === true;
                    return false;
                  })}
                  isScanning={activeTab === 'sast' ? isSastScanning : (activeTab === 'sca' || activeTab === 'container') ? isScaScanning : false}
                />
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', textAlign: 'center', padding: '40px' }}>
                  <div style={{
                    width: '80px',
                    height: '80px',
                    background: 'rgba(99, 102, 241, 0.1)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '20px'
                  }}>
                    <ShieldCheck size={40} color="var(--primary)" />
                  </div>
                  <h3 style={{ color: 'white', marginBottom: '8px' }}>Prêt pour l'analyse</h3>
                  <p style={{ maxWidth: '300px' }}>Cliquez sur le bouton "Analyser" pour détecter les failles de sécurité."</p>

                  {history.length > 0 && (
                    <div style={{ marginTop: '32px', width: '100%', maxWidth: '1000px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <p style={{ fontSize: '12px', margin: 0, textAlign: 'left', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>Historique des scans :</p>
                        <button
                          onClick={handleDeleteAllHistory}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--high)',
                            fontSize: '11px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            opacity: 0.7,
                            transition: 'opacity 0.2s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                          onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                        >
                          <RotateCcw size={12} />
                          Tout effacer
                        </button>
                      </div>
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                        maxHeight: '300px',
                        overflowY: 'auto',
                        paddingRight: '8px',
                        scrollbarWidth: 'thin',
                        scrollbarColor: 'var(--border) transparent'
                      }}>
                        {history.map(scan => (
                          <div
                            key={scan.id}
                            onClick={() => loadPastScan(scan.id)}
                            style={{
                              padding: '16px 20px',
                              background: 'rgba(255,255,255,0.03)',
                              border: '1px solid var(--border)',
                              borderRadius: '10px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              cursor: 'pointer',
                              fontSize: '13px',
                              transition: 'all 0.2s',
                              borderLeft: scan.total_issues > 10 ? '3px solid var(--high)' : scan.total_issues > 0 ? '3px solid var(--warning)' : '3px solid var(--success)'
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                              e.currentTarget.style.borderColor = 'var(--primary)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                              e.currentTarget.style.borderColor = 'var(--border)';
                            }}
                          >
                            <div className="flex flex-col gap-1" style={{ flex: 1 }}>
                              <div className="flex items-center gap-2">
                                <span style={{ fontWeight: 600 }}>Scan #{scan.id}</span>
                                <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>{new Date(scan.started_at).toLocaleString()}</span>
                              </div>
                              <div style={{ color: 'var(--text-bright)', fontSize: '12px', opacity: 0.8 }}>
                                {[
                                  scan.run_sast !== false && scan.scanner_type !== 'zap' && scan.scanner_type !== 'trivy' ? `${getScannerDisplayName(scan.scanner_type)} (SAST)` : null,
                                  scan.run_sca ? 'Dependency-Check' : null,
                                  scan.run_container || scan.scanner_type === 'trivy' ? 'Trivy (Container)' : null,
                                  scan.run_dast || scan.scanner_type === 'zap' ? 'ZAP (DAST)' : null
                                ].filter((item, pos, self) => Boolean(item) && self.indexOf(item) === pos).join(', ')}
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="flex flex-col items-end gap-1" style={{ minWidth: '100px' }}>
                                <span style={{
                                  color: scan.total_issues > 10 ? 'var(--high)' : scan.total_issues > 0 ? 'var(--warning)' : 'var(--success)',
                                  fontWeight: 'bold'
                                }}>
                                  {scan.total_issues} issues
                                </span>
                                <span className={`status-text ${scan.status.toLowerCase()}`} style={{ fontSize: '10px', textTransform: 'uppercase', opacity: 0.6 }}>
                                  {scan.status === 'COMPLETED' ? 'Terminé' : scan.status === 'FAILED' ? 'Échoué' : 'En cours'}
                                </span>
                              </div>
                              <button
                                onClick={(e) => handleDeleteScan(e, scan.id)}
                                disabled={isDeleting === scan.id}
                                style={{
                                  background: 'rgba(239, 68, 68, 0.1)',
                                  border: '1px solid rgba(239, 68, 68, 0.2)',
                                  borderRadius: '6px',
                                  padding: '8px',
                                  color: '#ef4444',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  transition: 'all 0.2s'
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.background = '#ef4444';
                                  e.currentTarget.style.color = 'white';
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
                                  e.currentTarget.style.color = '#ef4444';
                                }}
                              >
                                {isDeleting === scan.id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <ZeroVulnModal isOpen={showZeroModal} onClose={() => setShowZeroModal(false)} />

      <DeleteConfirmModal
        isOpen={deleteModalConfig.isOpen}
        onClose={() => setDeleteModalConfig({ ...deleteModalConfig, isOpen: false })}
        onConfirm={executeDeletion}
        type={deleteModalConfig.type}
      />

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

const ZeroVulnModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.2s ease-out'
    }}>
      <div className="card" style={{
        width: '100%',
        maxWidth: '400px',
        textAlign: 'center',
        padding: '40px 32px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
        animation: 'scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
      }}>
        <div style={{
          width: '72px',
          height: '72px',
          background: 'rgba(34, 197, 94, 0.1)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          border: '2px solid rgba(34, 197, 94, 0.2)'
        }}>
          <ShieldCheck size={40} color="#22c55e" />
        </div>

        <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '12px', color: 'white' }}>
          Scan Terminé
        </h2>
        <p style={{ color: 'var(--text-dim)', lineHeight: '1.6', marginBottom: '32px' }}>
          Félicitations ! Aucune vulnérabilité n'a été détectée. Votre code est conforme aux règles de sécurité.
        </p>

        <button
          onClick={onClose}
          style={{
            width: '100%',
            padding: '12px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'transform 0.2s, background 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
        >
          Fermer
        </button>
      </div>
    </div>
  );
};

const DeleteConfirmModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  type: 'single' | 'all';
}> = ({ isOpen, onClose, onConfirm, type }) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1100,
      padding: '20px',
      animation: 'fadeIn 0.2s ease-out'
    }}>
      <div className="card" style={{
        width: '100%',
        maxWidth: '420px',
        textAlign: 'center',
        padding: '32px',
        background: 'var(--bg-card)',
        border: '1px solid rgba(239, 68, 68, 0.2)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
        animation: 'scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
      }}>
        <div style={{
          width: '64px',
          height: '64px',
          background: 'rgba(239, 68, 68, 0.1)',
          borderRadius: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          border: '1px solid rgba(239, 68, 68, 0.2)'
        }}>
          <AlertTriangle size={32} color="#ef4444" />
        </div>

        <h2 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '12px', color: 'white' }}>
          {type === 'all' ? "Supprimer tout l'historique" : "Supprimer ce scan"}
        </h2>

        <p style={{ color: 'var(--text-dim)', lineHeight: '1.6', fontSize: '14px', marginBottom: '32px' }}>
          {type === 'all'
            ? "Êtes-vous certain de vouloir supprimer TOUT l'historique des scans de ce projet ? Cette action est irréversible."
            : "Voulez-vous vraiment supprimer ce scan ? Toutes les vulnérabilités associées seront également effacées."}
        </p>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: '12px',
              background: 'rgba(255,255,255,0.05)',
              color: 'white',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          >
            Annuler
          </button>
          <button
            onClick={onConfirm}
            style={{
              flex: 1,
              padding: '12px',
              background: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#dc2626'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#ef4444'}
          >
            Supprimer
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalysisPage;
