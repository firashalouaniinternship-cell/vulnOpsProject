import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  ShieldCheck, 
  Settings, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowRight,
  RefreshCcw,
  LayoutDashboard,
  FolderGit2,
  Lock,
  ExternalLink,
  Zap,
  Link,
  LogOut,
  Key,
  Globe
} from 'lucide-react';
import api, { endpoints } from '../api/client';
import logo from '../assets/logo.svg';

interface GitHubRepo {
  id: number;
  full_name: string;
  name: string;
  private: boolean;
  pipeline_status: 'pending' | 'installed' | 'error';
  setup_result?: any;
}

interface Installation {
  installation_id: number;
  github_account: string;
  account_type: string;
  repositories: GitHubRepo[];
  setup_completed: boolean;
  status: string;
}

const CICDPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [isAppInstalled, setIsAppInstalled] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [setupLoading, setSetupLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchUser();
    
    // Check if we just returned from an installation
    const installed = searchParams.get('installed');
    const installationId = searchParams.get('installation_id');
    
    if (installed === 'true' && installationId) {
      linkInstallation(installationId);
    }
  }, [searchParams]);

  const fetchUser = async () => {
    try {
      const res = await api.get(endpoints.auth.me);
      setUser(res.data);
    } catch (err) {
      navigate('/');
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await api.get(endpoints.githubApp.status);
      setIsAppInstalled(res.data.installed);
      setInstallations(res.data.installations || []);
    } catch (err) {
      console.error('Erreur fetchStatus:', err);
    } finally {
      setLoading(false);
    }
  };

  const linkInstallation = async (id: string) => {
    try {
      setLoading(true);
      await api.post(endpoints.githubApp.link, { installation_id: id });
      await fetchStatus();
      // Remove params from URL
      navigate('/cicd', { replace: true });
    } catch (err) {
      console.error('Erreur linkInstallation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async () => {
    try {
      const res = await api.get(endpoints.githubApp.install);
      window.location.href = res.data.install_url;
    } catch (err) {
      alert("Erreur lors de la récupération de l'URL d'installation.");
    }
  };

  const handleManualSetup = async (owner: string, repo: string) => {
    const fullName = `${owner}/${repo}`;
    setSetupLoading(fullName);
    try {
      await api.post(endpoints.githubApp.setup(owner, repo));
      await fetchStatus();
    } catch (err) {
      alert(`Erreur setup manuel pour ${fullName}`);
    } finally {
      setSetupLoading(null);
    }
  };
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0a0d14] text-white">
        <Loader2 className="animate-spin text-indigo-500" size={48} />
      </div>
    );
  }

  return (
    <div className="app-container" style={{ display: 'flex', minHeight: '100vh', background: '#0a0d14' }}>
      {/* Sidebar (Copy from ProjectsPage for consistency) */}
      <aside style={{
        width: '260px',
        background: '#0f121a',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        height: '100vh',
        zIndex: 100
      }}>
        <div style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '25px',
            height: '25px',
            background: 'white',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
          }}>
            <img src={logo} alt="Logo" style={{ width: '24px', height: '24px', objectFit: 'contain' }} />
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>VulnOps</h2>
        </div>

        <nav style={{ flex: 1, padding: '12px' }}>
          <NavItem icon={<LayoutDashboard size={20} />} label="Dashboard" onClick={() => navigate('/Dashboard')} />
          <NavItem icon={<FolderGit2 size={20} />} label="Mes Projets" onClick={() => navigate('/MesProjects')} />
          <NavItem icon={<Link size={20} />} label="Projet Externe" onClick={() => navigate('/ProjetExterne')} />
          <NavItem icon={<Globe size={20} />} label="CI/CD Integration" active />
          <NavItem icon={<Key size={20} />} label="Configuration LLM" onClick={() => navigate('/llm-config')} />
        </nav>

        <div style={{ padding: '20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            {user?.github_avatar_url ? (
              <img src={user.github_avatar_url} alt="Avatar" style={{ width: '36px', height: '36px', borderRadius: '50%' }} />
            ) : (
              <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--border)' }}></div>
            )}
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'white', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{user?.github_login}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Utilisateur</div>
            </div>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-2" style={{
            width: '100%',
            padding: '10px',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            background: 'transparent',
            color: 'var(--text-dim)',
            fontSize: '14px',
            cursor: 'pointer'
          }}>
            <LogOut size={16} />
            Déconnexion
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, marginLeft: '260px', padding: '40px' }}>
        <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <header style={{ marginBottom: '40px' }}>
            <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginBottom: '12px' }}>
              Intégration CI/CD <span style={{ color: 'var(--primary)' }}>Automatisée</span>
            </h1>
            <p style={{ color: 'var(--text-dim)', fontSize: '18px' }}>
              Connectez votre compte GitHub pour installer automatiquement nos pipelines de sécurité sur vos dépôts.
            </p>
          </header>

          {!isAppInstalled ? (
            <div className="card" style={{ 
              padding: '60px', 
              textAlign: 'center', 
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              borderRadius: '24px',
              animation: 'fadeIn 0.5s ease-out'
            }}>
              <div style={{ 
                width: '80px', 
                height: '80px', 
                background: 'var(--primary)', 
                borderRadius: '20px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                margin: '0 auto 24px',
                boxShadow: '0 10px 25px -5px rgba(99, 102, 241, 0.4)'
              }}>
                <ShieldCheck size={40} color="white" />
              </div>
              <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', marginBottom: '16px' }}>
                Prêt à passer au niveau supérieur ?
              </h2>
              <p style={{ color: 'var(--text-dim)', maxWidth: '500px', margin: '0 auto 32px', lineHeight: '1.6' }}>
                En installant l'application GitHub VulnOps, nous configurerons automatiquement vos workflows GitHub Actions et vos secrets de sécurité. Plus de configuration manuelle.
              </p>
              
              <div style={{ display: 'flex', justifyContent: 'center', gap: '40px', marginBottom: '48px' }}>
                <FeatureItem icon={<Zap size={20} />} text="Setup en 1 clic" />
                <FeatureItem icon={<Lock size={20} />} text="Secrets sécurisés" />
                <FeatureItem icon={<CheckCircle2 size={20} />} text="Scans auto" />
              </div>

              <button 
                onClick={handleInstall}
                style={{
                  padding: '16px 32px',
                  background: 'var(--primary)',
                  color: 'white',
                  borderRadius: '12px',
                  fontWeight: 'bold',
                  fontSize: '18px',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '0 auto',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 20px 25px -5px rgba(99, 102, 241, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                Connect GitHub App <ArrowRight size={20} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
              {/* Connected Header */}
              <div className="card" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ padding: '12px', background: 'rgba(34, 197, 94, 0.1)', borderRadius: '12px', color: '#22c55e' }}>
                    <CheckCircle2 size={24} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white' }}>GitHub App Installée</h3>
                    <p style={{ color: 'var(--text-dim)', fontSize: '14px' }}>
                      Connecté à {installations.length} compte(s) GitHub
                    </p>
                  </div>
                </div>
                <button 
                  onClick={handleInstall}
                  style={{
                    padding: '10px 20px',
                    background: 'rgba(255,255,255,0.05)',
                    color: 'white',
                    borderRadius: '8px',
                    fontSize: '14px',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Plus size={16} /> Ajouter une installation
                </button>
              </div>

              {/* Installations List */}
              {installations.map(inst => (
                <div key={inst.installation_id} style={{ animation: 'fadeIn 0.3s ease-out' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>
                      Compte: {inst.github_account}
                    </h2>
                    <span style={{ 
                      fontSize: '12px', 
                      padding: '2px 8px', 
                      background: 'rgba(99, 102, 241, 0.1)', 
                      color: 'var(--primary)', 
                      borderRadius: '4px',
                      border: '1px solid rgba(99, 102, 241, 0.2)'
                    }}>
                      {inst.account_type}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                    {inst.repositories.map(repo => (
                      <div key={repo.id} className="card" style={{ padding: '20px', position: 'relative' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <FolderGit2 size={20} color={repo.private ? '#f59e0b' : 'var(--primary)'} />
                            <span style={{ fontWeight: 600, color: 'white' }}>{repo.name}</span>
                          </div>
                          {repo.private && <span style={{ fontSize: '10px', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>Privé</span>}
                        </div>

                        <div style={{ marginBottom: '20px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', marginBottom: '8px' }}>
                            <div style={{ 
                              width: '8px', 
                              height: '8px', 
                              borderRadius: '50%', 
                              background: repo.pipeline_status === 'installed' ? '#22c55e' : (repo.pipeline_status === 'error' ? '#ef4444' : '#f59e0b')
                            }} />
                            <span style={{ color: 'var(--text-dim)' }}>
                              Pipeline: {repo.pipeline_status === 'installed' ? 'Installé' : (repo.pipeline_status === 'error' ? 'Erreur' : 'En attente')}
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
                            <CheckCircle2 size={14} color="#22c55e" />
                            <span style={{ color: 'var(--text-dim)' }}>Secrets configurés</span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '10px' }}>
                          <button 
                            onClick={() => handleManualSetup(inst.github_account, repo.name)}
                            disabled={setupLoading === repo.full_name}
                            style={{
                              flex: 1,
                              padding: '8px',
                              background: repo.pipeline_status === 'installed' ? 'rgba(34, 197, 94, 0.1)' : 'var(--primary)',
                              color: repo.pipeline_status === 'installed' ? '#22c55e' : 'white',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontWeight: 600,
                              border: repo.pipeline_status === 'installed' ? '1px solid rgba(34, 197, 94, 0.2)' : 'none',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '6px'
                            }}
                          >
                            {setupLoading === repo.full_name ? <Loader2 size={14} className="animate-spin" /> : <RefreshCcw size={14} />}
                            {repo.pipeline_status === 'installed' ? 'Réinstaller' : 'Installer'}
                          </button>
                          <a 
                            href={`https://github.com/${repo.full_name}/actions`} 
                            target="_blank" 
                            rel="noreferrer"
                            className="card"
                            style={{
                              padding: '8px',
                              background: 'transparent',
                              borderRadius: '6px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'var(--text-dim)'
                            }}
                          >
                            <ExternalLink size={16} />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

const NavItem: React.FC<{ icon: React.ReactNode; label: string; active?: boolean; onClick?: () => void }> = ({ icon, label, active, onClick }) => (
  <div
    onClick={onClick}
    style={{
      padding: '12px 16px',
      borderRadius: '8px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      cursor: 'pointer',
      background: active ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
      color: active ? 'var(--primary)' : 'var(--text-dim)',
      marginBottom: '4px',
      transition: 'all 0.2s',
      fontWeight: active ? 600 : 500
    }}
  >
    {icon}
    <span>{label}</span>
  </div>
);

const FeatureItem: React.FC<{ icon: React.ReactNode; text: string }> = ({ icon, text }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'white' }}>
    <div style={{ color: 'var(--primary)' }}>{icon}</div>
    <span style={{ fontSize: '14px', fontWeight: 500 }}>{text}</span>
  </div>
);

export default CICDPage;
