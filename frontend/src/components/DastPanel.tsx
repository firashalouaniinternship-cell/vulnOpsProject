import React, { useState, useEffect } from 'react';
import { Globe, ShieldAlert, CheckCircle, AlertCircle, Loader2, Play, ExternalLink, Info, Sparkles, Rocket } from 'lucide-react';
import api, { endpoints } from '../api/client';
import ScanResults from './ScanResults';

interface DastPanelProps {
  repoFullName: string;
  repoOwner: string;
  repoName: string;
  cloneUrl: string;
  customToken?: string;
  onScanComplete?: (data: any) => void;
  isRemoteScanning?: boolean;
}

const DastPanel: React.FC<DastPanelProps> = ({
  repoFullName,
  repoOwner,
  repoName,
  cloneUrl,
  customToken,
  onScanComplete,
  isRemoteScanning
}) => {
  const [targetUrl, setTargetUrl] = useState('');
  const [checking, setChecking] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [prereqs, setPrereqs] = useState<any>(null);
  const [showPrereqWarning, setShowPrereqWarning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customCommand, setCustomCommand] = useState('');
  const [customPort, setCustomPort] = useState('');
  const [scanResult, setScanResult] = useState<any>(null);

  // Check prerequisites on component mount
  useEffect(() => {
    checkPrerequisites();
  }, [repoFullName]);

  const checkPrerequisites = async () => {
    setChecking(true);
    setError(null);
    try {
      const response = await api.post(endpoints.scanner.dastCheck, {
        clone_url: cloneUrl,
        custom_token: customToken
      });
      setPrereqs(response.data);
    } catch (err: any) {
      console.error('Error checking DAST prerequisites:', err);
      setError('Impossible de vérifier les prérequis du dépôt.');
    } finally {
      setChecking(false);
    }
  };

  const handleStartScan = async (force = false) => {
    if (!targetUrl) {
      setError('Veuillez entrer une URL cible valide.');
      return;
    }

    // Check if ready, if not and not forced, show the warning popup
    if (prereqs && !prereqs.ready && !force) {
      setShowPrereqWarning(true);
      return;
    }

    setScanning(true);
    setShowPrereqWarning(false);
    setError(null);

    try {
      const response = await api.post(endpoints.scanner.dastScan, {
        repo_full_name: repoFullName,
        repo_owner: repoOwner,
        repo_name: repoName,
        target_url: targetUrl
      });
      
      setScanResult(response.data);
      if (onScanComplete) onScanComplete(response.data);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Échec du scan DAST. Vérifiez que Docker est actif sur le serveur.');
    } finally {
      setScanning(false);
    }
  };

  const handleStartAutoScan = async () => {
    setScanning(true);
    setScanResult(null);
    setError(null);

    try {
      const response = await api.post(endpoints.scanner.dastAutoScan, {
        clone_url: cloneUrl,
        repo_full_name: repoFullName,
        repo_owner: repoOwner,
        repo_name: repoName,
        custom_token: customToken,
        start_command: customCommand || undefined,
        target_port: customPort ? parseInt(customPort) : undefined
      });
      
      setScanResult(response.data);
      if (onScanComplete) onScanComplete(response.data);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Échec du build ou du scan automatique. Vérifiez les logs Docker.');
    } finally {
      setScanning(false);
    }
  };

  const isAnyScanning = scanning || isRemoteScanning;

  return (
    <div className="dast-panel" style={{ padding: '24px', height: '100%', overflowY: 'auto', position: 'relative' }}>
      {isRemoteScanning && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          padding: '12px',
          background: 'rgba(99, 102, 241, 0.1)',
          borderBottom: '1px solid var(--primary)',
          color: 'white',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          backdropFilter: 'blur(4px)',
          animation: 'fadeIn 0.3s ease-out'
        }}>
          <Loader2 size={18} className="animate-spin" />
          <span style={{ fontWeight: 600 }}>Un scan DAST automatisé est en cours d'exécution...</span>
        </div>
      )}
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <header style={{ marginBottom: '32px' }}>
          <div className="flex items-center gap-3" style={{ marginBottom: '12px' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              background: 'rgba(239, 68, 68, 0.1)', 
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Globe size={24} color="#ef4444" />
            </div>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>DAST Analysis (ZAP)</h2>
              <p style={{ fontSize: '14px', color: 'var(--text-dim)' }}>
                Analyse dynamique de votre application en cours d'exécution.
              </p>
            </div>
          </div>
        </header>

        {/* Option 1: Automated Local Scan (Premium Card) */}
        <section className="card" style={{ 
          marginBottom: '32px', 
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(239, 68, 68, 0.1) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          padding: '24px',
          overflow: 'hidden'
        }}>
          <div className="flex justify-between items-start mb-6">
            <div style={{ flex: 1 }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={20} color="#f59e0b" />
                Analyse Automatisée (Docker Build)
              </h3>
              <p style={{ fontSize: '14px', color: 'var(--text-dim)', maxWidth: '500px' }}>
                Nous construisons l'image de votre projet, lançons le conteneur localement et effectuons le scan sans aucune configuration.
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <button
                onClick={handleStartAutoScan}
                disabled={isAnyScanning || checking}
                style={{
                  padding: '12px 24px',
                  background: 'var(--primary)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: (isAnyScanning || checking) ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                }}
              >
                {isAnyScanning ? <Loader2 size={18} className="animate-spin" /> : <Rocket size={18} />}
                {isAnyScanning ? 'Progression...' : 'Build & Scan'}
              </button>

              {/* <button 
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline' }}
              >
                {showAdvanced ? 'Masquer les options' : 'Options avancées'}
              </button> */}
            </div>
          </div>

          {showAdvanced && (
            <div style={{ 
              marginBottom: '24px', 
              padding: '16px', 
              background: 'rgba(0,0,0,0.2)', 
              borderRadius: '8px',
              border: '1px dashed rgba(255,255,255,0.1)',
              animation: 'fadeIn 0.2s ease-out'
            }}>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px', textTransform: 'uppercase' }}>Port Interne</label>
                  <input 
                    type="text" 
                    placeholder="Auto-détecté (ex: 8000)" 
                    value={customPort}
                    onChange={(e) => setCustomPort(e.target.value)}
                    style={{ width: '100%', padding: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '4px', color: 'white', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px', textTransform: 'uppercase' }}>Commande Start (CMD Override)</label>
                  <input 
                    type="text" 
                    placeholder="Ignorer CMD (ex: python main.py)" 
                    value={customCommand}
                    onChange={(e) => setCustomCommand(e.target.value)}
                    style={{ width: '100%', padding: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '4px', color: 'white', fontSize: '13px' }}
                  />
                </div>
              </div>
              
              {prereqs?.dockerfile_content && (
                 <div style={{ marginTop: '16px' }}>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px', textTransform: 'uppercase' }}>Aperçu du Dockerfile</label>
                    <pre style={{ 
                      maxHeight: '150px', 
                      overflowY: 'auto', 
                      background: '#0a0f1d', 
                      padding: '12px', 
                      borderRadius: '4px', 
                      fontSize: '12px', 
                      color: '#94a3b8',
                      border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                      <code>{prereqs?.dockerfile_content}</code>
                    </pre>
                 </div>
              )}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            <div style={{ textAlign: 'center', opacity: scanning ? 1 : 0.5 }}>
              <div style={{ margin: '0 auto 8px', width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center' }}>1</div>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Build Image</span>
            </div>
            <div style={{ textAlign: 'center', opacity: scanning ? 1 : 0.5 }}>
              <div style={{ margin: '0 auto 8px', width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center' }}>2</div>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Run App</span>
            </div>
            <div style={{ textAlign: 'center', opacity: scanning ? 1 : 0.5 }}>
              <div style={{ margin: '0 auto 8px', width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center' }}>3</div>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>ZAP Scan</span>
            </div>
            <div style={{ textAlign: 'center', opacity: scanning ? 1 : 0.5 }}>
              <div style={{ margin: '0 auto 8px', width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center' }}>4</div>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Cleanup</span>
            </div>
          </div>
        </section>

        <div style={{ 
          height: '1px', 
          background: 'var(--border)', 
          margin: '32px 0', 
          position: 'relative',
          display: 'flex',
          justifyContent: 'center'
        }}>
          <span style={{ position: 'absolute', top: '-10px', background: '#0f172a', padding: '0 16px', fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>OU</span>
        </div>

        {/* Option 2: Manual URL Scan */}
        <section className="card" style={{ marginBottom: '24px', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', marginBottom: '16px' }}>
            Scanner une URL manuellement
          </h3>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: 600, marginBottom: '8px', color: 'white' }}>
              Cible de l'analyse
            </label>
            <div className="flex gap-2">
              <div style={{ position: 'relative', flex: 1 }}>
                <Globe size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="url"
                  placeholder="https://votre-app-active.com"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 12px 12px 36px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'white',
                    outline: 'none'
                  }}
                />
              </div>
              <button
                onClick={() => handleStartScan()}
                disabled={scanning || checking}
                style={{
                  padding: '0 24px',
                  background: 'var(--primary)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: (scanning || checking) ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  opacity: (scanning || checking) ? 0.7 : 1
                }}
              >
                {scanning ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
                {scanning ? 'Scan en cours...' : 'Lancer le scan'}
              </button>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '8px' }}>
              ZAP effectuera un scan "Baseline" (passif) sur l'URL fournie.
            </p>
          </div>

          <div style={{ 
            padding: '16px', 
            background: 'rgba(255,255,255,0.02)', 
            borderRadius: '8px',
            border: '1px solid var(--border)'
          }}>
            <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={16} color={prereqs?.ready ? "#10b981" : "var(--text-dim)"} />
              Vérification du dépôt
            </h4>
            {checking ? (
              <div className="flex items-center gap-2" style={{ color: 'var(--text-dim)', fontSize: '13px' }}>
                <Loader2 size={14} className="animate-spin" />
                Vérification des fichiers Docker et OpenAPI...
              </div>
            ) : prereqs ? (
              <div className="flex flex-col gap-2">
                <PrereqItem label="Dockerfile / Compose" met={prereqs.found?.dockerfile || prereqs.found?.compose} />
                <PrereqItem label="Spécification OpenAPI" met={prereqs.found?.openapi} />
              </div>
            ) : null}
          </div>
        </section>

        {error && (
          <div style={{ 
            padding: '16px', 
            background: 'rgba(239, 68, 68, 0.1)', 
            border: '1px solid #ef4444', 
            borderRadius: '8px',
            color: '#fca5a5',
            fontSize: '14px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        {/* Results section */}
        {scanResult && scanResult.vulnerabilities && (
          <div style={{ animation: 'scaleIn 0.3s ease-out', marginTop: '32px' }}>
             <div className="flex items-center justify-between mb-6">
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', color: 'white' }}>
                  <CheckCircle size={20} color="#10b981" /> Résultats du Scan DAST
                </h3>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--high)' }}></div>
                    <span style={{ fontSize: '14px', color: 'white' }}>{scanResult.vulnerabilities.filter((v: any) => v.severity === 'HIGH').length} Haut</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--warning)' }}></div>
                    <span style={{ fontSize: '14px', color: 'white' }}>{scanResult.vulnerabilities.filter((v: any) => v.severity === 'MEDIUM').length} Moyen</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--low)' }}></div>
                    <span style={{ fontSize: '14px', color: 'white' }}>{scanResult.vulnerabilities.filter((v: any) => v.severity === 'LOW').length} Bas</span>
                  </div>
                </div>
             </div>

             <div className="flex flex-col gap-4">
                {scanResult.vulnerabilities.length === 0 ? (
                  <div className="card" style={{ padding: '40px', textAlign: 'center', background: 'rgba(255,255,255,0.02)' }}>
                    <CheckCircle size={40} color="#10b981" style={{ margin: '0 auto 16px', opacity: 0.5 }} />
                    <p style={{ color: 'var(--text-dim)' }}>Aucune vulnérabilité détectée par ZAP sur {scanResult.target_url || targetUrl}.</p>
                  </div>
                ) : (
                  <ScanResults vulnerabilities={scanResult.vulnerabilities} />
                )}
             </div>
          </div>
        )}
      </div>

      {/* Prerequisite Missing Pop-up */}
      {showPrereqWarning && (
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
            maxWidth: '500px', 
            width: '90%', 
            padding: '32px', 
            textAlign: 'center',
            border: '1px solid var(--border)',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
          }}>
            <div style={{ 
              width: '64px', 
              height: '64px', 
              background: 'rgba(245, 158, 11, 0.1)', 
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px'
            }}>
              <ShieldAlert size={32} color="#f59e0b" />
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px', color: 'white' }}>
              Prérequis manquants
            </h3>
            <p style={{ color: 'var(--text-dim)', marginBottom: '24px', lineHeight: '1.5' }}>
              Votre projet semble manquer de certains fichiers recommandés pour une analyse DAST automatisée optimale (ZAP peut mieux scanner s'il y a un fichier OpenAPI/Swagger).
            </p>
            
            <div style={{ 
              background: 'rgba(255,255,255,0.03)', 
              borderRadius: '8px', 
              padding: '16px', 
              textAlign: 'left',
              marginBottom: '24px',
              fontSize: '13px'
            }}>
              <p style={{ fontWeight: 600, marginBottom: '8px', color: 'white' }}>Éléments manquants :</p>
              <ul style={{ listStyle: 'disc', paddingLeft: '20px', color: '#fca5a5' }}>
                {prereqs?.missing.map((m: string, i: number) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowPrereqWarning(false)}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'white',
                  cursor: 'pointer'
                }}
              >
                Annuler
              </button>
              <button
                onClick={() => handleStartScan(true)}
                style={{
                  flex: 1,
                  padding: '12px',
                  background: '#f59e0b',
                  border: 'none',
                  borderRadius: '8px',
                  color: 'black',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Continuer quand même
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const PrereqItem: React.FC<{ label: string; met: boolean }> = ({ label, met }) => (
  <div className="flex items-center justify-between" style={{ fontSize: '13px' }}>
    <span style={{ color: 'var(--text-dim)' }}>{label}</span>

    {met ? (
      <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <CheckCircle size={14} /> Détecté
      </span>
    ) : (
      <span style={{ color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <AlertCircle size={14} /> Non trouvé
      </span>
    )}
  </div>
);

export default DastPanel;
