import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Search, FolderGit2, Star, GitFork, ExternalLink, Loader2, LogOut, 
  LayoutDashboard, Shield, Globe, Lock, Code2, Clock, Link
} from 'lucide-react';
import api, { endpoints } from '../api/client';

interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  private: boolean;
  html_url: string;
  updated_at: string;
  has_scans?: boolean;
}

const ProjectsPage: React.FC = () => {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [user, setUser] = useState<any>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const getActiveViewFromPath = (path: string) => {
    if (path === '/Dashboard') return 'dashboard';
    if (path === '/MesProjects') return 'projects';
    if (path === '/ProjetExterne') return 'external';
    return (location.state as any)?.view || 'dashboard';
  };

  const [activeView, setActiveView] = useState<'dashboard' | 'projects' | 'external'>(
    getActiveViewFromPath(location.pathname)
  );

  useEffect(() => {
    setActiveView(getActiveViewFromPath(location.pathname));
  }, [location.pathname]);
  const [filterType, setFilterType] = useState<'all' | 'public' | 'private'>('all');
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  
  // External Project State
  const [extUrl, setExtUrl] = useState('');
  const [extToken, setExtToken] = useState('');
  const [extLoading, setExtLoading] = useState(false);
  const handleExternalProjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extUrl) return;

    setExtLoading(true);
    try {
      const match = extUrl.match(/github\.com\/([^\/]+)\/([^\/]+)/);
      if (!match) {
        alert("Veuillez entrer une URL GitHub valide.");
        setExtLoading(false);
        return;
      }
      const owner = match[1];
      const repo = match[2].replace('.git', '');

      const headers: any = {};
      if (extToken) {
        headers['Authorization'] = `token ${extToken}`;
      }

      const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`, { headers });
      if (!response.ok) {
        alert("token obligatoire pour les projets privé");
        setExtLoading(false);
        return;
      }

      const data = await response.json();
      navigate(`/analysis/${data.full_name}`, { 
        state: { 
          language: data.language,
          cloneUrl: data.clone_url,
          customToken: extToken 
        } 
      });
    } catch (error) {
      console.error(error);
      alert("Une erreur est survenue lors de la vérification du dépôt.");
    } finally {
      setExtLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userRes, reposRes, statsRes] = await Promise.all([
          api.get(endpoints.auth.me),
          api.get(endpoints.projects.list),
          api.get(endpoints.scanner.dashboardStats).catch(() => ({ data: null }))
        ]);
        setUser(userRes.data);
        setRepos(reposRes.data);
        if (statsRes.data) {
          setDashboardStats(statsRes.data);
        }
      } catch (err) {
        console.error('Erreur lors du chargement des données:', err);
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await api.post(endpoints.auth.logout);
      navigate('/');
    } catch (err) {
      console.error('Erreur lors de la déconnexion:', err);
    }
  };

  const filteredRepos = repos.filter(repo => {
    const matchesSearch = repo.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (repo.description && repo.description.toLowerCase().includes(searchTerm.toLowerCase()));
    
    if (!matchesSearch) return false;
    
    if (filterType === 'public') return !repo.private;
    if (filterType === 'private') return repo.private;
    return true; // 'all'
  });

  // Derived statistics for dashboard
  const stats = {
    total: repos.length,
    public: repos.filter(r => !r.private).length,
    private: repos.filter(r => r.private).length,
    languages: Array.from(new Set(repos.map(r => r.language).filter(Boolean))).length,
    topLanguage: repos.reduce((acc, curr) => {
      if (!curr.language) return acc;
      acc[curr.language] = (acc[curr.language] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  };

  const topLanguage = Object.entries(stats.topLanguage)
    .sort(([, a], [, b]) => b - a)[0]?.[0] || 'N/A';

  return (
    <div className="app-container" style={{ display: 'flex', minHeight: '100vh', background: '#0a0d14' }}>
      {/* Sidebar */}
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
          <Shield size={32} color="var(--primary)" />
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white' }}>VulnOps</h2>
        </div>

        <nav style={{ flex: 1, padding: '12px' }}>
          <div 
            onClick={() => navigate('/Dashboard')}
            style={{ 
              padding: '12px 16px', 
              borderRadius: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              cursor: 'pointer',
              background: activeView === 'dashboard' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
              color: activeView === 'dashboard' ? 'var(--primary)' : 'var(--text-dim)',
              marginBottom: '4px',
              transition: 'all 0.2s'
            }}
          >
            <LayoutDashboard size={20} />
            <span style={{ fontWeight: 500 }}>Dashboard</span>
          </div>

          <div 
            onClick={() => navigate('/MesProjects')}
            style={{ 
              padding: '12px 16px', 
              borderRadius: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              cursor: 'pointer',
              background: activeView === 'projects' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
              color: activeView === 'projects' ? 'var(--primary)' : 'var(--text-dim)',
              marginBottom: '4px',
              transition: 'all 0.2s'
            }}
          >
            <FolderGit2 size={20} />
            <span style={{ fontWeight: 500 }}>Mes Projets</span>
          </div>

          <div 
            onClick={() => navigate('/ProjetExterne')}
            style={{ 
              padding: '12px 16px', 
              borderRadius: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              cursor: 'pointer',
              background: activeView === 'external' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
              color: activeView === 'external' ? 'var(--primary)' : 'var(--text-dim)',
              transition: 'all 0.2s'
            }}
          >
            <Link size={20} />
            <span style={{ fontWeight: 500 }}>Projet Externe</span>
          </div>
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
        {activeView === 'dashboard' ? (
          <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px', color: 'white' }}>Bonjour, {user?.github_login} 👋</h1>
            <p style={{ color: 'var(--text-dim)', marginBottom: '32px' }}>Voici un aperçu de l'utilisation de votre plateforme VulnOps.</p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', marginBottom: '40px' }}>
              <StatCard title="Total Dépôts" value={stats.total} icon={<FolderGit2 size={24} color="var(--primary)" />} trend="+2 ce mois" />
              <StatCard title="Dépôts Publics" value={stats.public} icon={<Globe size={24} color="#3b82f6" />} />
              <StatCard title="Dépôts Privés" value={stats.private} icon={<Lock size={24} color="#f59e0b" />} />
              <StatCard title="Langages" value={stats.languages} icon={<Code2 size={24} color="#ec4899" />} subtitle={`Top: ${topLanguage}`} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
              <div className="card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '20px', color: 'white' }}>Activité Récente</h3>
                {dashboardStats?.recent_scans && dashboardStats.recent_scans.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {dashboardStats.recent_scans.map((scan: any) => (
                      <div 
                        key={scan.id} 
                        style={{ 
                          padding: '12px', 
                          background: 'rgba(255,255,255,0.03)', 
                          border: '1px solid var(--border)', 
                          borderRadius: '8px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                        onClick={() => navigate(`/analysis/${scan.repo_full_name}`, { state: { fromDashboard: true } })}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                          e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                          e.currentTarget.style.borderColor = 'var(--border)';
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 500, color: 'white', marginBottom: '4px' }}>{scan.repo_full_name}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                            {scan.scanner_type} • {new Date(scan.started_at).toLocaleString()}
                          </div>
                        </div>
                        <div>
                          {scan.status === 'COMPLETED' ? (
                            <span style={{ color: scan.total_issues > 0 ? 'var(--high)' : 'var(--success)', fontWeight: 500, fontSize: '14px' }}>
                              {scan.total_issues} issue(s)
                            </span>
                          ) : (
                            <span style={{ color: 'var(--warning)', fontSize: '12px' }}>{scan.status}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '40px' }}>
                    <Clock size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
                    <p>Aucune activité récente trouvée.</p>
                  </div>
                )}
              </div>
              <div className="card" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '20px', color: 'white' }}>Utilisation API</h3>
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '8px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Appels RAG</span>
                    <span style={{ color: 'white' }}>
                      {dashboardStats?.api_usage?.rag_calls_count || 0}/{dashboardStats?.api_usage?.rag_calls_limit || 100}
                    </span>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${Math.min(100, ((dashboardStats?.api_usage?.rag_calls_count || 0) / (dashboardStats?.api_usage?.rag_calls_limit || 100)) * 100)}%`, 
                      height: '100%', 
                      background: 'var(--primary)', 
                      borderRadius: '3px',
                      transition: 'width 0.5s ease-out'
                    }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : activeView === 'external' ? (
          <div style={{ animation: 'fadeIn 0.3s ease-out', maxWidth: '600px', margin: '0 auto' }}>
            <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px', color: 'white' }}>Scanner un Projet Externe</h1>
            <p style={{ color: 'var(--text-dim)', marginBottom: '32px' }}>
              Insérez l'URL d'un dépôt GitHub public ou fournissez un token pour scanner un dépôt privé.
            </p>

            <form onSubmit={handleExternalProjectSubmit} className="card" style={{ padding: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: 'white', fontWeight: 500 }}>URL du dépôt GitHub</label>
                <input 
                  type="url" 
                  required
                  placeholder="https://github.com/owner/repo" 
                  value={extUrl}
                  onChange={(e) => setExtUrl(e.target.value)}
                  autoComplete="off"
                  style={{ 
                    width: '100%', 
                    padding: '12px', 
                    background: 'var(--bg-secondary)', 
                    border: '1px solid var(--border)', 
                    borderRadius: '8px', 
                    color: 'white',
                    fontSize: '14px',
                    outline: 'none'
                  }}
                />
              </div>

              <div style={{ marginBottom: '32px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: 'white', fontWeight: 500 }}>
                  Personal Access Token <span style={{ color: 'var(--text-dim)', fontSize: '12px', fontWeight: 'normal' }}>(Optionnel pour public, Requis pour privé)</span>
                </label>
                <input 
                  type="password" 
                  placeholder="ghp_xxxxxxxxxxxx" 
                  value={extToken}
                  onChange={(e) => setExtToken(e.target.value)}
                  autoComplete="new-password"
                  style={{ 
                    width: '100%', 
                    padding: '12px', 
                    background: 'var(--bg-secondary)', 
                    border: '1px solid var(--border)', 
                    borderRadius: '8px', 
                    color: 'white',
                    fontSize: '14px',
                    outline: 'none'
                  }}
                />
                <p style={{ color: 'var(--text-dim)', fontSize: '12px', marginTop: '8px' }}>
                  Ce token est uniquement utilisé pour la validation et l'analyse, et ne sera pas sauvegardé dans notre base de données.
                </p>
              </div>

              <button 
                type="submit" 
                disabled={extLoading || !extUrl}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: 'var(--primary)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: (extLoading || !extUrl) ? 'not-allowed' : 'pointer',
                  opacity: (extLoading || !extUrl) ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'background 0.2s'
                }}
              >
                {extLoading ? <Loader2 size={18} className="animate-spin" /> : <Shield size={18} />}
                {extLoading ? 'Vérification...' : 'Ajouter project to scan'}
              </button>
            </form>
          </div>
        ) : (
          <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <div className="flex items-center justify-between" style={{ marginBottom: '32px' }}>
              <div>
                <h1 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '8px', color: 'white' }}>Vos Projets GitHub</h1>
                <p style={{ color: 'var(--text-dim)' }}>Sélectionnez un dépôt pour lancer une analyse de sécurité.</p>
              </div>
              
              <div className="flex items-center" style={{ gap: '16px' }}>
                <select 
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value as any)}
                  style={{
                    padding: '10px 12px',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '14px',
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="all">Tous les dépôts</option>
                  <option value="public">Dépôts Publics</option>
                  <option value="private">Dépôts Privés</option>
                </select>

                <div style={{ position: 'relative', width: '300px' }}>
                  <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                  <input 
                    type="text" 
                    placeholder="Rechercher un dépôt..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{ 
                      width: '100%', 
                      padding: '10px 12px 10px 40px', 
                      background: 'var(--bg-card)', 
                      border: '1px solid var(--border)', 
                      borderRadius: '8px', 
                      color: 'white',
                      fontSize: '14px'
                    }}
                  />
                </div>
              </div>
            </div>

            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-dim)' }}>
                <Loader2 size={48} className="animate-spin" style={{ marginBottom: '16px' }} />
                <p>Chargement de vos dépôts...</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                {filteredRepos.map(repo => (
                  <div 
                    key={repo.id} 
                    className="card" 
                    style={{ 
                      cursor: 'pointer', 
                      transition: 'transform 0.2s, border 0.2s, background 0.2s, opacity 0.2s', 
                      position: 'relative',
                      border: repo.has_scans ? '1px solid var(--border)' : '1px dashed rgba(207, 30, 30, 0.92)',
                      opacity: repo.has_scans ? 1 : 0.95,
                      background: repo.has_scans ? 'var(--bg-card)' : 'rgba(200, 23, 23, 0.41)'
                    }}
                    onClick={() => navigate(`/analysis/${repo.full_name}`, { state: { language: repo.language } })}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-4px)';
                      if (!repo.has_scans) e.currentTarget.style.borderColor = 'var(--primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      if (!repo.has_scans) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)';
                    }}
                  >
                    <div className="flex items-center justify-between" style={{ marginBottom: '12px' }}>
                      <FolderGit2 size={20} color={repo.private ? 'var(--warning)' : (repo.has_scans ? 'var(--primary)' : 'var(--text-dim)')} />
                      <div className="flex gap-2">
                        {!repo.has_scans && (
                          <span style={{ 
                            fontSize: '10px', 
                            fontWeight: 600, 
                            color: 'var(--text-dim)', 
                            background: 'rgba(255,255,255,0.05)',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            border: '1px solid rgba(255,255,255,0.1)'
                          }}>
                            NOUVEAU
                          </span>
                        )}
                        {repo.private && <span className="badge badge-medium">Privé</span>}
                        <a 
                          href={repo.html_url} 
                          target="_blank" 
                          rel="noreferrer" 
                          onClick={(e) => e.stopPropagation()}
                          style={{ color: 'var(--text-dim)' }}
                        >
                          <ExternalLink size={16} />
                        </a>
                      </div>
                    </div>
                    <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {repo.name}
                    </h3>
                    <p style={{ color: 'var(--text-dim)', fontSize: '14px', marginBottom: '20px', height: '40px', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                      {repo.description || 'Pas de description'}
                    </p>
                    <div className="flex items-center justify-between" style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      <div className="flex items-center gap-3">
                        {repo.language && (
                          <span className="flex items-center gap-1">
                            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: repo.language === 'Python' ? '#3572A5' : '#858585' }}></span>
                            {repo.language}
                          </span>
                        )}
                        {!repo.has_scans ? (
                          <span style={{ color: 'var(--primary)', fontWeight: 500, fontSize: '11px' }}>
                            ✨ Prêt pour analyse
                          </span>
                        ) : (
                          <>
                            <span className="flex items-center gap-1"><Star size={12} /> {repo.stars}</span>
                            <span className="flex items-center gap-1"><GitFork size={12} /> {repo.forks}</span>
                          </>
                        )}
                      </div>
                      <span>{repo.has_scans ? `Màj ${new Date(repo.updated_at).toLocaleDateString()}` : 'Jamais scanné'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!loading && filteredRepos.length === 0 && (
              <div style={{ textAlign: 'center', padding: '64px', color: 'var(--text-dim)' }}>
                <p>Aucun dépôt trouvé.</p>
              </div>
            )}
          </div>
        )}
      </main>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

const StatCard: React.FC<{ title: string; value: number | string; icon: React.ReactNode; trend?: string; subtitle?: string }> = ({ title, value, icon, trend, subtitle }) => (
  <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
      <span style={{ color: 'var(--text-dim)', fontSize: '18px', fontWeight: 600 }}>{title}</span>
      <div style={{ display: 'flex', alignItems: 'center' }}>{icon}</div>
    </div>
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
      <span style={{ fontSize: '32px', fontWeight: 'bold', color: 'white' }}>{value}</span>
      {trend && <span style={{ fontSize: '12px', color: 'var(--success)' }}>{trend}</span>}
    </div>
    {subtitle && <div style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{subtitle}</div>}
  </div>
);

export default ProjectsPage;
