import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

export const endpoints = {
  auth: {
    github: '/accounts/github/login/',
    login: '/accounts/login/',
    register: '/accounts/register/',
    me: '/accounts/me/',
    logout: '/accounts/logout/',
  },
  projects: {
    list: '/projects/repos/',
    tree: (owner: string, repo: string) => `/projects/${owner}/${repo}/tree/`,
    branches: (owner: string, repo: string) => `/projects/${owner}/${repo}/branches/`,
    file: (owner: string, repo: string) => `/projects/${owner}/${repo}/file/`,
  },
  scanner: {
    scan: '/scanner/scan/',
    history: (owner: string, repo: string) => `/scanner/history/${owner}/${repo}/`,
    detail: (scanId: number) => `/scanner/detail/${scanId}/`,
    autoSelect: '/scanner/auto-select/',
    autoScan: '/scanner/auto-scan/',
    analyze: '/scanner/analyze/',
    recommendation: (vulnId: number) => `/scanner/vulnerability/${vulnId}/recommendation/`,
    patch: (vulnId: number) => `/scanner/vulnerability/${vulnId}/patch/`,
    dashboardStats: '/scanner/dashboard-stats/',
    dastCheck: '/scanner/dast/check-prerequisites/',
    dastScan: '/scanner/dast/scan/',
    dastAutoScan: '/scanner/dast/auto-scan/',
  },
  ai: {
    chat: '/ai/chat/',
  },
  githubApp: {
    install: '/github-app/install/',
    status: '/github-app/status/',
    repos: '/github-app/repos/',
    setup: (owner: string, repo: string) => `/github-app/setup/${owner}/${repo}/`,
    link: '/github-app/link/',
  },
};
