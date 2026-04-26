import React, { useState, useEffect } from 'react';
import logo from '../assets/logo.svg';
import { GitBranch, ShieldAlert, Loader2, Search, Key, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api, { endpoints } from '../api/client';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'login' | 'anonymous'>('login');

  // Fast Scan Form State
  const [repoUrl, setRepoUrl] = useState('');
  const [customToken, setCustomToken] = useState('');
  const [isFastScanLoading, setIsFastScanLoading] = useState(false);

  // Manual Auth State
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [manualLoading, setManualLoading] = useState(false);

  // Vérifie si on revient du callback GitHub
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    // Supprime les paramètres de l'URL pour garder une interface propre
    if (code || state) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleGitHubLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(endpoints.auth.github);
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      } else {
        setError("Erreur : L'URL d'authentification n'a pas été reçue.");
      }
    } catch (err: any) {
      console.error('Erreur lors de l\'initialisation de la connexion:', err);
      const errorMsg = err.response?.data?.error ||
        'Impossible de contacter le serveur. Vérifiez que le backend Django est lancé.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleManualAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setManualLoading(true);
    setError(null);
    try {
      if (isRegistering) {
        await api.post(endpoints.auth.register, { username, email, password });
      } else {
        await api.post(endpoints.auth.login, { username, password });
      }
      // Success -> check user and redirect
      const userRes = await api.get(endpoints.auth.me);
      if (userRes.data.is_github_user) {
        navigate('/MesProjects');
      } else {
        navigate('/InternalDashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Erreur d\'authentification');
    } finally {
      setManualLoading(false);
    }
  };

  const handleFastScan = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!repoUrl.trim()) {
      setError("Veuillez entrer l'URL du dépôt GitHub (ex: owner/repo)");
      return;
    }

    // Parse l'url pour extraire owner et repo
    let owner = '';
    let repo = '';

    try {
      const cleanUrl = repoUrl.trim().replace(/\/$/, "");
      if (cleanUrl.includes('github.com')) {
        const urlObj = new URL(cleanUrl.startsWith('http') ? cleanUrl : `https://${cleanUrl}`);
        const pathParts = urlObj.pathname.split('/').filter(p => p);
        if (pathParts.length >= 2) {
          owner = pathParts[0];
          repo = pathParts[1].replace('.git', '');
        }
      } else {
        const parts = cleanUrl.split('/');
        if (parts.length === 2) {
          owner = parts[0];
          repo = parts[1];
        }
      }

      if (!owner || !repo) {
        throw new Error("Format invalide");
      }

      setIsFastScanLoading(true);
      // On redirige avec les params en state pour que AnalysisPage s'en serve
      navigate(`/analysis/${owner}/${repo}`, {
        state: {
          customToken: customToken.trim() || undefined,
          cloneUrl: `https://github.com/${owner}/${repo}.git`
        }
      });
      setIsFastScanLoading(false);

    } catch (err) {
      setError("L'URL du dépôt n'est pas valide. Format attendu : owner/repo ou https://github.com/owner/repo");
      setIsFastScanLoading(false);
    }
  };


  return (
    <div className="auth-layout" style={{
      background: 'radial-gradient(circle at top right, #1e1b4b 0%, #0f172a 100%)',
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh'
    }}>
      {/* Éléments décoratifs en arrière-plan */}
      <div style={{ position: 'absolute', top: '10%', right: '10%', width: '300px', height: '300px', background: 'var(--primary)', filter: 'blur(120px)', opacity: 0.1, pointerEvents: 'none' }}></div>
      <div style={{ position: 'absolute', bottom: '10%', left: '10%', width: '250px', height: '250px', background: '#4f46e5', filter: 'blur(100px)', opacity: 0.1, pointerEvents: 'none' }}></div>

      <div className="card" style={{
        width: '100%',
        maxWidth: '440px',
        padding: '40px',
        zIndex: 1,
        backdropFilter: 'blur(12px)',
        background: 'rgba(30, 41, 59, 0.7)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{
            width: '72px',
            height: '72px',
            background: 'linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%)',
            borderRadius: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 8px 16px -4px rgba(99, 102, 241, 0.4)',
            overflow: 'hidden'
          }}>
            <img src={logo} alt="VulnOps Logo" style={{ width: '100%', height: '100%', objectFit: 'contain', padding: '12px' }} />
          </div>
          <h1 style={{ fontSize: '32px', fontWeight: 800, marginBottom: '8px', letterSpacing: '-0.025em', color: 'white' }}>VulnOps</h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '15px', lineHeight: '1.5' }}>
            Sécurité automatisée pour vos développements.
          </p>
        </div>

        {/* Message d'erreur */}
        {error && (
          <div style={{
            padding: '12px',
            marginBottom: '20px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            color: '#fca5a5',
            fontSize: '13px',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        {viewMode === 'login' ? (
          <div style={{ animation: 'fadeIn 0.5s ease-out' }}>
            <div style={{ marginBottom: '24px', textAlign: 'center' }}>
              <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', marginBottom: '8px' }}>
                {isRegistering ? 'Rejoindre la plateforme' : 'Authentification'}
              </h2>
              <p style={{ color: 'var(--text-dim)', fontSize: '14px' }}>
                {isRegistering ? 'Créez votre profil pour commencer l\'analyse.' : 'Heureux de vous revoir sur VulnOps.'}
              </p>
            </div>

            <form onSubmit={handleManualAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ position: 'relative' }}>
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Nom d'utilisateur"
                  style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '8px', color: 'white', outline: 'none' }}
                  required
                />
              </div>

              {isRegistering && (
                <div style={{ position: 'relative' }}>
                  <input 
                    type="email" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email"
                    style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '8px', color: 'white', outline: 'none' }}
                    required
                  />
                </div>
              )}

              <div style={{ position: 'relative' }}>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Mot de passe"
                  style={{ width: '100%', padding: '12px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '8px', color: 'white', outline: 'none' }}
                  required
                />
              </div>

              <button 
                type="submit"
                disabled={manualLoading}
                className="btn-primary"
                style={{ 
                  width: '100%', 
                  padding: '14px', 
                  fontSize: '16px',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  cursor: manualLoading ? 'not-allowed' : 'pointer'
                }}
              >
                {manualLoading ? <Loader2 size={20} className="animate-spin" /> : (isRegistering ? 'S\'inscrire' : 'Se connecter')}
              </button>
            </form>

            <div style={{ display: 'flex', alignItems: 'center', margin: '24px 0', gap: '16px' }}>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontWeight: 600 }}>OU</span>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
            </div>

            <button
              onClick={handleGitHubLogin}
              disabled={loading}
              style={{
                width: '100%',
                padding: '14px',
                background: 'white',
                color: '#0f172a',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 'bold',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              {loading ? <Loader2 size={20} className="animate-spin" /> : <GitBranch size={20} />}
              Continuer avec GitHub
            </button>

            <div style={{ marginTop: '24px', textAlign: 'center' }}>
              <button 
                onClick={() => setIsRegistering(!isRegistering)}
                style={{ background: 'none', border: 'none', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer', fontSize: '14px' }}
              >
                {isRegistering ? 'Déjà un compte ? Se connecter' : 'Pas de compte ? S\'inscrire'}
              </button>
            </div>

            {/* 
            <div style={{ display: 'flex', alignItems: 'center', marginTop: '20px', gap: '12px', justifyContent: 'center' }}>
              <button onClick={() => setViewMode('anonymous')} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', fontSize: '13px', cursor: 'pointer' }}>
                Continuer sans compte
              </button>
            </div>
            */}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', animation: 'slideDown 0.3s ease-out' }}>
            {/* Fast Scan Form */}
            <form onSubmit={handleFastScan} style={{ display: 'flex', flexDirection: 'column', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Search size={18} color="var(--primary)" />
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'white' }}>Analyse Rapide (Anonyme)</h3>
              </div>

              <div style={{ position: 'relative' }}>
                <GitBranch size={16} color="var(--text-dim)" style={{ position: 'absolute', top: '50%', transform: 'translateY(-50%)', left: '12px' }} />
                <input
                  type="text"
                  placeholder="owner/repo (ex: PyCQA/bandit)"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 12px 12px 40px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '14px',
                    outline: 'none',
                    transition: 'border-color 0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)'}
                />
              </div>

              <div style={{ position: 'relative' }}>
                <Key size={16} color="var(--text-dim)" style={{ position: 'absolute', top: '50%', transform: 'translateY(-50%)', left: '12px' }} />
                <input
                  type="password"
                  placeholder="Token GitHub (Optionnel pour public)"
                  value={customToken}
                  onChange={(e) => setCustomToken(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 12px 12px 40px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '14px',
                    outline: 'none',
                    transition: 'border-color 0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)'}
                />
              </div>

              <button
                type="submit"
                disabled={isFastScanLoading}
                style={{
                  width: '100%',
                  padding: '12px',
                  backgroundColor: 'rgba(255,255,255,0.05)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  marginTop: '8px',
                  transition: 'all 0.2s',
                  cursor: isFastScanLoading ? 'not-allowed' : 'pointer'
                }}
                onMouseEnter={(e) => {
                  if (!isFastScanLoading) {
                    e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.15)';
                    e.currentTarget.style.borderColor = 'var(--primary)';
                    e.currentTarget.style.color = 'white';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.color = 'var(--text-main)';
                }}
              >
                {isFastScanLoading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                Lancer l'analyse
              </button>
            </form>

            {/* Toggle back to login */}
            <div style={{ display: 'flex', alignItems: 'center', margin: '8px 0 0 0', gap: '16px' }}>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
              <button
                type="button"
                onClick={() => setViewMode('login')}
                style={{
                  background: 'none', border: 'none', color: 'var(--text-dim)',
                  fontSize: '13px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em',
                  cursor: 'pointer', transition: 'color 0.2s', padding: 0
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-main)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
              >
                Retour à la connexion
              </button>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default LoginPage;

