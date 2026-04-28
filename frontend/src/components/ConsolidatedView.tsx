import React, { useMemo } from 'react';
import { Shield, ShieldAlert, Zap, Box, Code, Layout, ExternalLink, Filter, BarChart3 } from 'lucide-react';
import { type Vulnerability } from './ScanResults';

interface ConsolidatedViewProps {
  vulnerabilities: Vulnerability[];
}

const ConsolidatedView: React.FC<ConsolidatedViewProps> = ({ vulnerabilities }) => {
  // Deduplication Logic
  const consolidated = useMemo(() => {
    const groups: Record<string, Vulnerability & { sources: string[] }> = {};

    vulnerabilities.forEach(v => {
      // Create a unique key for deduplication
      // We use filename, line_number and either CWE or a normalized test name
      const type = v.cwe || v.test_id || v.test_name;
      const key = `${v.filename}:${v.line_number}:${type}`;

      if (groups[key]) {
        // Merge sources
        if (!groups[key].sources.includes(v.test_name)) {
          groups[key].sources.push(v.test_name);
        }
        // Take the highest severity if they differ
        const severityOrder = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
        const currentSeverity = v.severity?.toUpperCase() || 'LOW';
        const existingSeverity = groups[key].severity?.toUpperCase() || 'LOW';
        
        if ((severityOrder as any)[currentSeverity] > (severityOrder as any)[existingSeverity]) {
          groups[key].severity = v.severity;
        }
      } else {
        groups[key] = {
          ...v,
          sources: [v.test_name]
        };
      }
    });

    return Object.values(groups).sort((a, b) => {
      const severityOrder = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
      const sevA = a.severity?.toUpperCase() || 'LOW';
      const sevB = b.severity?.toUpperCase() || 'LOW';
      return (severityOrder as any)[sevB] - (severityOrder as any)[sevA];
    });
  }, [vulnerabilities]);

  // Metrics
  const metrics = useMemo(() => {
    return {
      total: consolidated.length,
      critical: consolidated.filter(v => v.severity === 'CRITICAL').length,
      high: consolidated.filter(v => v.severity === 'HIGH').length,
      medium: consolidated.filter(v => v.severity === 'MEDIUM').length,
      low: consolidated.filter(v => v.severity === 'LOW').length,
      layers: {
        sast: vulnerabilities.filter(v => !v.is_sca && !v.is_container && !v.is_dast).length,
        sca: vulnerabilities.filter(v => v.is_sca).length,
        container: vulnerabilities.filter(v => v.is_container).length,
        dast: vulnerabilities.filter(v => v.is_dast).length,
      }
    };
  }, [consolidated, vulnerabilities]);

  const getSeverityColor = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MEDIUM': return '#eab308';
      case 'LOW': return '#3b82f6';
      default: return 'var(--text-dim)';
    }
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Summary Header */}
      <div style={{ 
        padding: '24px', 
        background: 'rgba(99, 102, 241, 0.03)', 
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'white', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Layout size={20} className="text-primary" />
              Rapport de Sécurité Consolidé
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-dim)', maxWidth: '600px' }}>
              Cette vue fusionne les résultats de tous les scanners actifs et élimine les doublons pour vous offrir une vision claire de la posture de sécurité de votre projet.
            </p>
          </div>

        </div>

        {/* Global Stats Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
          <StatCard label="Unique Issues" value={metrics.total} icon={<Shield size={16} />} color="var(--primary)" />
          <StatCard label="Critique" value={metrics.critical} icon={<ShieldAlert size={16} />} color="#ef4444" />
          <StatCard label="Haute" value={metrics.high} icon={<ShieldAlert size={16} />} color="#f97316" />
          <StatCard label="Moyenne" value={metrics.medium} icon={<Shield size={16} />} color="#eab308" />
          <StatCard label="Faible" value={metrics.low} icon={<Shield size={16} />} color="#3b82f6" />
        </div>

        {/* Layer Breakdown */}
        <div style={{ display: 'flex', gap: '24px', fontSize: '12px', color: 'var(--text-dim)', padding: '0 4px' }}>
          <LayerStat label="SAST" value={metrics.layers.sast} icon={<Code size={12} />} />
          <LayerStat label="SCA" value={metrics.layers.sca} icon={<Box size={12} />} />
          <LayerStat label="Container" value={metrics.layers.container} icon={<Zap size={12} />} />
          <LayerStat label="DAST" value={metrics.layers.dast} icon={<Layout size={12} />} />
        </div>
      </div>

      {/* Findings List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Détails des Vulnérabilités ({consolidated.length})
          </h4>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            Déduplication active: <strong>{vulnerabilities.length - consolidated.length}</strong> doublons masqués
          </div>
        </div>

        {consolidated.map((vuln, idx) => (
          <div 
            key={idx}
            className="conso-card"
            style={{
              padding: '20px',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--border)',
              borderRadius: '12px',
              borderLeft: `4px solid ${getSeverityColor(vuln.severity)}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              transition: 'all 0.2s'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ 
                    fontSize: '11px', 
                    fontWeight: 700, 
                    color: getSeverityColor(vuln.severity),
                    textTransform: 'uppercase',
                    background: `${getSeverityColor(vuln.severity)}15`,
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>
                    {vuln.severity}
                  </span>
                  <span style={{ fontWeight: 600, color: 'white' }}>{vuln.test_name}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>({vuln.test_id})</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Code size={12} />
                  {vuln.filename}{vuln.line_number > 0 && `:${vuln.line_number}`}
                  {vuln.cwe && <span style={{ marginLeft: '12px', opacity: 0.7 }}>{vuln.cwe}</span>}
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'flex-end', maxWidth: '300px' }}>
                {vuln.sources.map((s, i) => (
                  <span key={i} style={{ 
                    fontSize: '10px', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    background: 'rgba(99, 102, 241, 0.1)', 
                    color: 'var(--primary)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    fontWeight: 600
                  }}>
                    Detected by {s}
                  </span>
                ))}
              </div>
            </div>

            <p style={{ fontSize: '14px', color: 'var(--text-bright)', lineHeight: '1.5' }}>
              {vuln.issue_text}
            </p>

            {vuln.code_snippet && (
              <pre style={{ 
                margin: 0,
                padding: '12px', 
                background: 'rgba(0,0,0,0.3)', 
                borderRadius: '8px', 
                fontSize: '11px', 
                overflow: 'auto',
                border: '1px solid rgba(255,255,255,0.05)',
                fontFamily: 'monospace'
              }}>
                <code style={{ color: '#e5e7eb' }}>{vuln.code_snippet}</code>
              </pre>
            )}
          </div>
        ))}
      </div>

      <style>{`
        .conso-card:hover {
          background: rgba(255,255,255,0.04) !important;
          transform: translateX(4px);
          border-color: var(--primary) !important;
        }
      `}</style>
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: number; icon: React.ReactNode; color: string }> = ({ label, value, icon, color }) => (
  <div style={{ 
    padding: '12px', 
    background: 'rgba(255,255,255,0.02)', 
    border: '1px solid var(--border)', 
    borderRadius: '10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-dim)', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' }}>
      <div style={{ color }}>{icon}</div>
      {label}
    </div>
    <div style={{ fontSize: '20px', fontWeight: 700, color: value > 0 ? 'white' : 'var(--text-dim)' }}>
      {value}
    </div>
  </div>
);

const LayerStat: React.FC<{ label: string; value: number; icon: React.ReactNode }> = ({ label, value, icon }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
    <div style={{ color: value > 0 ? 'var(--primary)' : 'var(--text-dim)', opacity: 0.8 }}>{icon}</div>
    <span style={{ opacity: value > 0 ? 1 : 0.5 }}>{label}:</span>
    <strong style={{ color: value > 0 ? 'white' : 'inherit' }}>{value}</strong>
  </div>
);

export default ConsolidatedView;
