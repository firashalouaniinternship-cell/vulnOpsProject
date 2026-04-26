import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ShieldCheck, 
  FileCode, 
  Settings, 
  LogOut, 
  Plus, 
  Search, 
  Terminal, 
  AlertTriangle, 
  CheckCircle2, 
  Clock,
  Shield,
  Activity,
  Zap
} from 'lucide-react';
import api, { endpoints } from '../api/client';

const InternalDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await api.get(endpoints.auth.me);
        if (res.data.is_github_user) {
          navigate('/MesProjects');
          return;
        }
        setUser(res.data);
      } catch (err) {
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await api.post(endpoints.auth.logout);
      navigate('/');
    } catch (err) {
      console.error('Logout failed', err);
    }
  };

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f172a' }}>
        <div className="animate-spin" style={{ width: '40px', height: '40px', border: '3px solid var(--primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0f1e', color: 'white', fontFamily: 'Inter, sans-serif' }}>
      {/* Sidebar - Design différent et plus sombre */}
      <aside style={{ 
        width: '280px', 
        background: 'rgba(15, 23, 42, 0.8)', 
        backdropFilter: 'blur(10px)',
        borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '40px' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldCheck size={24} color="white" />
          </div>
          <span style={{ fontSize: '20px', fontWeight: 'bold', letterSpacing: '-0.02em' }}>VulnOps <span style={{ color: 'var(--primary)', fontSize: '12px', verticalAlign: 'top' }}>PRO</span></span>
        </div>

        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {[
            { id: 'overview', icon: LayoutDashboard, label: 'Tableau de bord' },
            { id: 'projects', icon: FileCode, label: 'Mes Projets Locaux' },
            { id: 'audits', icon: Shield, label: 'Audits de Sécurité' },
            { id: 'activity', icon: Activity, label: 'Flux d\'activité' },
            { id: 'settings', icon: Settings, label: 'Paramètres' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '12px',
                border: 'none',
                background: activeTab === item.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                color: activeTab === item.id ? '#818cf8' : '#94a3b8',
                cursor: 'pointer',
                fontWeight: activeTab === item.id ? 600 : 500,
                transition: 'all 0.2s ease',
                textAlign: 'left'
              }}
            >
              <item.icon size={20} />
              {item.label}
            </button>
          ))}
        </nav>

        <div style={{ marginTop: 'auto', padding: '16px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.username}</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Compte Interne</div>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '8px', padding: '8px', borderRadius: '8px', border: 'none', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
          >
            <LogOut size={16} />
            Déconnexion
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <h1 style={{ fontSize: '32px', fontWeight: 'bold', marginBottom: '8px' }}>Tableau de bord</h1>
            <p style={{ color: '#64748b' }}>Bienvenue sur votre espace de sécurité privé.</p>
          </div>
          <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px' }}>
            <Plus size={20} />
            Nouveau Projet Local
          </button>
        </header>

        {/* Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', marginBottom: '40px' }}>
          {[
            { label: 'Projets Actifs', value: '0', icon: FileCode, color: '#6366f1' },
            { label: 'Vulnérabilités', value: '0', icon: AlertTriangle, color: '#f59e0b' },
            { label: 'Scans Effectués', value: '0', icon: Zap, color: '#10b981' },
            { label: 'Score Moyen', value: 'N/A', icon: CheckCircle2, color: '#8b5cf6' },
          ].map((stat, i) => (
            <div key={i} style={{ padding: '24px', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '20px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: `${stat.color}15`, color: stat.color, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>
                <stat.icon size={24} />
              </div>
              <div style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '4px' }}>{stat.value}</div>
              <div style={{ fontSize: '14px', color: '#64748b' }}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Empty State / Welcome Section */}
        <div style={{ 
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)', 
          borderRadius: '24px', 
          padding: '60px', 
          textAlign: 'center',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '200px', height: '200px', background: 'var(--primary)', filter: 'blur(100px)', opacity: 0.1 }}></div>
          
          <div style={{ maxWidth: '600px', margin: '0 auto' }}>
            <div style={{ width: '80px', height: '80px', borderRadius: '24px', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
              <Terminal size={40} color="#6366f1" />
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px' }}>Commencez à sécuriser votre code</h2>
            <p style={{ color: '#94a3b8', fontSize: '16px', lineHeight: '1.6', marginBottom: '32px' }}>
              Vous êtes actuellement connecté avec un compte interne. Cette interface vous permet de gérer vos projets sans dépendre de GitHub. Vous pouvez bientôt uploader des archives ZIP ou spécifier des chemins locaux pour analyse.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
              <button style={{ padding: '12px 24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'white', fontWeight: 600, cursor: 'pointer' }}>
                Importer un Projet
              </button>
              <button style={{ padding: '12px 24px', borderRadius: '12px', border: 'none', background: 'white', color: '#0f172a', fontWeight: 600, cursor: 'pointer' }}>
                Guide de démarrage
              </button>
            </div>
          </div>
        </div>

        {/* Recent Activity Placeholder */}
        <div style={{ marginTop: '40px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold' }}>Activité récente</h3>
            <button style={{ background: 'none', border: 'none', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer' }}>Voir tout</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[1, 2, 3].map(i => (
              <div key={i} style={{ padding: '16px 24px', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '16px', opacity: 0.5 }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#64748b' }}></div>
                <div style={{ flex: 1, fontSize: '14px', color: '#94a3b8' }}>Aucun événement récent enregistré. Commencez par ajouter un projet.</div>
                <div style={{ fontSize: '12px', color: '#475569' }}><Clock size={12} style={{ marginRight: '4px' }} /> À l'instant</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default InternalDashboard;
