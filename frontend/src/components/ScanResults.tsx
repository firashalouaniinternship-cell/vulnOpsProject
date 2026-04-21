import React, { useState } from 'react';
import { AlertTriangle, AlertCircle, Info, ChevronRight, Code, Sparkles, Loader2, BookOpen, CheckCircle, Globe, Filter, RefreshCw } from 'lucide-react';
import api, { endpoints } from '../api/client';

export interface Vulnerability {
  id: number;
  test_id: string;
  test_name: string;
  issue_text: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: string;
  filename: string;
  line_number: number;
  code_snippet: string;
  cwe: string;
  more_info: string;
  llm_score?: number;
  llm_explanation?: string;
  is_sca?: boolean;
  is_container?: boolean;
  is_dast?: boolean;
  solution?: string;
}

interface ScanResultsProps {
  vulnerabilities: Vulnerability[];
  onSelectVuln?: (vuln: Vulnerability) => void;
  isScanning?: boolean;
}

const ScanResults: React.FC<ScanResultsProps> = ({ vulnerabilities, onSelectVuln, isScanning }) => {
  const [recommendations, setRecommendations] = useState<Record<number, { text: string, sources: number[], loading: boolean, error?: string, cached?: boolean }>>({});
  const [activeTabs, setActiveTabs] = useState<Record<number, 'code' | 'rag'>>({});
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');


  // Sort vulnerabilities by LLM score descending
  const sortedVulns = [...vulnerabilities].sort((a, b) => {
    const scoreA = a.llm_score ?? 0;
    const scoreB = b.llm_score ?? 0;
    if (scoreB !== scoreA) return scoreB - scoreA;
    
    // Fallback to severity
    const severityMap = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
    return severityMap[b.severity] - severityMap[a.severity];
  });

  const filteredVulns = sortedVulns.filter(v => 
    severityFilter === 'ALL' || v.severity === severityFilter
  );

  const counts = {
    ALL: vulnerabilities.length,
    CRITICAL: vulnerabilities.filter(v => v.severity === 'CRITICAL').length,
    HIGH: vulnerabilities.filter(v => v.severity === 'HIGH').length,
    MEDIUM: vulnerabilities.filter(v => v.severity === 'MEDIUM').length,
    LOW: vulnerabilities.filter(v => v.severity === 'LOW').length,
  };


  const fetchRecommendation = async (vulnId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (recommendations[vulnId]?.loading) return;

    setRecommendations(prev => ({
      ...prev,
      [vulnId]: { text: '', sources: [], loading: true }
    }));
    
    // Auto-switch to RAG tab when starting fetch
    setActiveTabs(prev => ({ ...prev, [vulnId]: 'rag' }));

    try {
      const response = await api.post(endpoints.scanner.recommendation(vulnId));
      setRecommendations(prev => ({
        ...prev,
        [vulnId]: { 
          text: response.data.result, 
          sources: response.data.sources || [], 
          loading: false,
          cached: response.data.cached === true
        }
      }));
    } catch (err: any) {
      console.error('Erreur RAG:', err);
      setRecommendations(prev => ({
        ...prev,
        [vulnId]: { 
          text: '', 
          sources: [], 
          loading: false, 
          error: err.response?.data?.error || 'Erreur lors de la récupération de la recommandation' 
        }
      }));
    }
  };

  const regenerateRecommendation = async (vulnId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (recommendations[vulnId]?.loading) return;

    setRecommendations(prev => ({
      ...prev,
      [vulnId]: { text: '', sources: [], loading: true }
    }));
    setActiveTabs(prev => ({ ...prev, [vulnId]: 'rag' }));

    try {
      const response = await api.post(`${endpoints.scanner.recommendation(vulnId)}?force=true`);
      setRecommendations(prev => ({
        ...prev,
        [vulnId]: {
          text: response.data.result,
          sources: response.data.sources || [],
          loading: false,
          cached: false
        }
      }));
    } catch (err: any) {
      console.error('Erreur RAG régénération:', err);
      setRecommendations(prev => ({
        ...prev,
        [vulnId]: {
          text: recommendations[vulnId]?.text || '',
          sources: recommendations[vulnId]?.sources || [],
          loading: false,
          cached: recommendations[vulnId]?.cached,
          error: err.response?.data?.error || 'Erreur lors de la régénération'
        }
      }));
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <span className="badge badge-critical">Critique</span>;
      case 'HIGH': return <span className="badge badge-high">Haute</span>;
      case 'MEDIUM': return <span className="badge badge-medium">Moyenne</span>;
      case 'LOW': return <span className="badge badge-low">Faible</span>;
      default: return null;
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <AlertCircle size={18} color="var(--critical)" />;
      case 'HIGH': return <AlertTriangle size={18} color="var(--high)" />;
      case 'MEDIUM': return <AlertTriangle size={18} color="var(--warning)" />;
      case 'LOW': return <Info size={18} color="var(--low)" />;
      default: return <AlertCircle size={18} />;
    }
  };

  if (vulnerabilities.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
        <p>Aucune vulnérabilité trouvée pour le moment.</p>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
      {/* Filtering Toolbar */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: '20px',
        padding: '12px 16px',
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        backdropFilter: 'blur(10px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-dim)', fontSize: '13px', marginRight: '8px' }}>
            <Filter size={14} />
            <span>Filtrer par sévérité:</span>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            {[
              { id: 'ALL', label: 'Toutes', color: 'var(--text-dim)', count: counts.ALL },
              { id: 'CRITICAL', label: 'Critique', color: 'var(--critical)', count: counts.CRITICAL },
              { id: 'HIGH', label: 'Haute', color: 'var(--high)', count: counts.HIGH },
              { id: 'MEDIUM', label: 'Moyenne', color: 'var(--warning)', count: counts.MEDIUM },
              { id: 'LOW', label: 'Faible', color: 'var(--low)', count: counts.LOW }
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setSeverityFilter(f.id as any)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  background: severityFilter === f.id ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                  border: '1px solid',
                  borderColor: severityFilter === f.id ? f.color : 'transparent',
                  borderRadius: '8px',
                  color: severityFilter === f.id ? 'white' : 'var(--text-dim)',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
                onMouseEnter={(e) => {
                  if (severityFilter !== f.id) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                    e.currentTarget.style.color = 'white';
                  }
                }}
                onMouseLeave={(e) => {
                  if (severityFilter !== f.id) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-dim)';
                  }
                }}
              >
                <div style={{ 
                  width: '6px', 
                  height: '6px', 
                  borderRadius: '50%', 
                  background: f.id === 'ALL' ? 'var(--primary)' : f.color,
                  boxShadow: severityFilter === f.id ? `0 0 8px ${f.id === 'ALL' ? 'var(--primary)' : f.color}` : 'none'
                }}></div>
                {f.label}
                <span style={{ 
                  opacity: 0.5, 
                  fontSize: '10px',
                  background: 'rgba(255,255,255,0.1)',
                  padding: '0px 6px',
                  borderRadius: '10px'
                }}>{f.count}</span>
              </button>
            ))}
          </div>
          {isScanning && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', fontSize: '12px', fontWeight: 600 }}>
              <Loader2 size={14} className="animate-spin" />
              <span>Scan en cours...</span>
            </div>
          )}
        </div>
        
        <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Affichage de <strong>{filteredVulns.length}</strong> sur {vulnerabilities.length} vulnérabilités
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filteredVulns.length === 0 ? (
          <div style={{ 
            padding: '40px', 
            textAlign: 'center', 
            color: 'var(--text-dim)',
            background: 'rgba(255,255,255,0.01)',
            borderRadius: '12px',
            border: '1px dashed var(--border)'
          }}>
            <p>Aucune vulnérabilité avec la sévérité "{severityFilter}" n'a été trouvée.</p>
          </div>
        ) : filteredVulns.map((vuln, idx) => {

          const rec = recommendations[vuln.id];
          const activeTab = activeTabs[vuln.id] || 'code';
          
          return (
            <div 
              key={vuln.id || idx}
              className="card"
              onClick={() => onSelectVuln?.(vuln)}
              style={{ 
                padding: '16px', 
                background: 'rgba(255,255,255,0.02)', 
                borderColor: 'var(--border)', 
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                flexDirection: 'column'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                e.currentTarget.style.borderColor = 'var(--primary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.02)';
                e.currentTarget.style.borderColor = 'var(--border)';
              }}
            >
              {/* Header */}
              <div className="flex justify-between items-center" style={{ marginBottom: '12px' }}>
                <div className="flex items-center gap-3">
                  {getSeverityIcon(vuln.severity)}
                  <span style={{ fontWeight: 'bold' }}>{vuln.test_name}</span>
                  <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>({vuln.test_id})</span>
                </div>
                <div className="flex items-center gap-2">
                  {vuln.llm_score !== undefined && vuln.llm_score > 0 && (
                     <div 
                      title={vuln.llm_explanation}
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '4px',
                        background: 'rgba(99, 102, 241, 0.1)',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        border: '1px solid rgba(99, 102, 241, 0.2)',
                        fontSize: '12px',
                        color: 'var(--primary)',
                        fontWeight: 'bold'
                      }}
                     >
                       <Sparkles size={12} />
                       Score AI: {vuln.llm_score.toFixed(2)}
                     </div>
                  )}
                  {getSeverityBadge(vuln.severity)}
                </div>
              </div>

              {/* Description */}
              <p style={{ fontSize: '14px', marginBottom: '16px' }}>{vuln.issue_text}</p>

              {/* Tab Navigation */}
              <div style={{ 
                display: 'flex', 
                gap: '24px', 
                borderBottom: '1px solid var(--border)', 
                marginBottom: '16px',
                paddingBottom: '2px'
              }}>
                <button 
                  onClick={(e) => { e.stopPropagation(); setActiveTabs(prev => ({ ...prev, [vuln.id]: 'code' })); }}
                  style={{ 
                    padding: '8px 4px', 
                    background: 'none', 
                    border: 'none', 
                    borderBottom: activeTab === 'code' ? '2px solid var(--primary)' : '2px solid transparent',
                    color: activeTab === 'code' ? 'var(--primary)' : 'var(--text-dim)',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s'
                  }}
                >
                  <Code size={14} />
                  {vuln.is_dast ? 'Evidence & Solution' : 'Détails & Code'}
                </button>
                {!vuln.is_dast && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!rec) {
                        fetchRecommendation(vuln.id, e);
                      } else {
                        setActiveTabs(prev => ({ ...prev, [vuln.id]: 'rag' }));
                      }
                    }}
                    style={{ 
                      padding: '8px 4px', 
                      background: 'none', 
                      border: 'none', 
                      borderBottom: activeTab === 'rag' ? '2px solid var(--primary)' : '2px solid transparent',
                      color: activeTab === 'rag' ? 'var(--primary)' : 'var(--text-dim)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.2s'
                    }}
                  >
                    {rec?.loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    Conseil AI
                  </button>
                )}
              </div>

              {/* Tab Content */}
              <div className="tab-content" style={{ minHeight: '100px' }}>
                {activeTab === 'code' ? (
                  <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
                    <div className="flex items-center gap-4 mb-3" style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      <span className="flex items-center gap-1">
                        {vuln.is_dast ? <Globe size={12} /> : <Code size={12} />}
                        {vuln.filename}{!vuln.is_dast && `:${vuln.line_number}`}
                      </span>
                      {vuln.cwe && <span>{vuln.cwe}</span>}
                    </div>
                    {vuln.code_snippet && (
                      <pre style={{ 
                        padding: '12px', 
                        background: '#0a0f1d', 
                        borderRadius: '6px', 
                        fontSize: '12px', 
                        overflowX: 'auto',
                        borderLeft: `2px solid var(--${vuln.severity.toLowerCase()})`
                      }}>
                        <code>{vuln.code_snippet}</code>
                      </pre>
                    )}
                    {vuln.is_dast && vuln.solution && (
                      <div style={{ marginTop: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontSize: '12px', fontWeight: 600, marginBottom: '8px', textTransform: 'uppercase' }}>
                          <CheckCircle size={14} /> Recommended Solution
                        </div>
                        <div style={{ 
                          padding: '12px', 
                          background: 'rgba(16, 185, 129, 0.05)', 
                          border: '1px solid rgba(16, 185, 129, 0.2)', 
                          borderRadius: '6px', 
                          fontSize: '13px',
                          color: 'var(--text-bright)',
                          lineHeight: '1.5'
                        }}>
                          {vuln.solution}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ animation: 'fadeIn 0.2s ease-out' }}>
                    {!rec || rec.loading ? (
                      <div style={{ 
                        padding: '24px', 
                        textAlign: 'center', 
                        color: 'var(--text-dim)',
                        background: 'rgba(99, 102, 241, 0.05)',
                        borderRadius: '6px',
                        border: '1px dashed rgba(99, 102, 241, 0.2)'
                      }}>
                        <Loader2 size={24} className="animate-spin mx-auto mb-3" style={{ opacity: 0.5 }} />
                        <p style={{ fontSize: '13px' }}>Analyse des connaissances OWASP et génération du conseil...</p>
                      </div>
                    ) : rec.error ? (
                      <div style={{ 
                        padding: '16px', 
                        background: 'rgba(239, 68, 68, 0.1)', 
                        border: '1px solid rgba(239, 68, 68, 0.2)', 
                        borderRadius: '6px',
                        color: 'var(--high)',
                        fontSize: '13px'
                      }}>
                        {rec.error}
                        <button 
                          onClick={(e) => fetchRecommendation(vuln.id, e)}
                          style={{ marginLeft: '10px', textDecoration: 'underline', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
                        >
                          Réessayer
                        </button>
                      </div>
                    ) : (
                      <div style={{ 
                        padding: '16px', 
                        background: 'rgba(99, 102, 241, 0.05)', 
                        border: '1px solid rgba(99, 102, 241, 0.2)', 
                        borderRadius: '6px',
                        fontSize: '13px',
                        color: 'var(--text-bright)'
                      }}>
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2" style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>
                              <Sparkles size={14} />
                              Expert Security Analysis
                            </div>
                            <div className="flex items-center gap-2">
                              {rec.cached && (
                                <span style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  color: '#10b981',
                                  background: 'rgba(16, 185, 129, 0.1)',
                                  border: '1px solid rgba(16, 185, 129, 0.2)',
                                  padding: '2px 8px',
                                  borderRadius: '10px'
                                }}>
                                  ⚡ Depuis le cache
                                </span>
                              )}
                              <button
                                onClick={(e) => regenerateRecommendation(vuln.id, e)}
                                title="Régénérer le conseil AI"
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '2px 8px',
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  color: 'var(--text-dim)',
                                  background: 'rgba(255,255,255,0.05)',
                                  border: '1px solid var(--border)',
                                  borderRadius: '10px',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s'
                                }}
                                onMouseEnter={e => { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'var(--primary)'; }}
                                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-dim)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                              >
                                <RefreshCw size={10} />
                                Régénérer
                              </button>
                            </div>
                          </div>
                          <div style={{ 
                            lineHeight: '1.6', 
                            whiteSpace: 'pre-wrap'
                          }}>
                            {rec.text}
                          </div>
                          {rec.sources && rec.sources.length > 0 && (
                            <div className="mt-4 pt-3 flex items-center gap-1" style={{ fontSize: '11px', color: 'var(--text-dim)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                              <BookOpen size={12} />
                              <span>Source: OWASP Top 10 for LLMs - Page(s) {rec.sources.join(', ')}</span>
                            </div>
                          )}
                        </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default ScanResults;
