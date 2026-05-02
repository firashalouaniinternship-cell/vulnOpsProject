/**
 * Hook React pour l'auto-sélection des scanners
 * Usage: const { selectScanners, autoScan, analyzeProject, loading, error } = useAutoScannerSelection();
 */

import { useState } from 'react';
import api, { endpoints } from '../api/client';

interface AutoSelectResult {
  success: boolean;
  repo_full_name: string;
  scan_mode: string;
  analysis: {
    languages: string[];
    frameworks: Record<string, string[]>;
    file_counts: Record<string, number>;
    structure_summary: string;
  };
  suggested_scanners: string[];
  reasoning: string;
  confidence: number;
  source: 'ai' | 'fallback' | 'mode:fast';
}

interface AutoScanResult {
  success: boolean;
  repo_full_name: string;
  scan_mode: string;
  scan_types: {
    sast: boolean;
    sca: boolean;
    container: boolean;
    dast: boolean;
  };
  selected_sast_scanners: string[];
  detection: {
    source: string;
    reasoning: string;
    confidence: number;
    analysis?: Record<string, any>;
  };
  scan_results: Array<{
    scanner: string;
    status: 'COMPLETED' | 'FAILED' | 'RUNNING';
    metrics?: Record<string, number>;
    error?: string;
    scan_id: number;
  }>;
}

interface AnalyzeResult {
  success: boolean;
  analysis: {
    languages: string[];
    frameworks: Record<string, string[]>;
    file_counts: Record<string, number>;
    structure_summary: string;
  };
  suggested_scanners: string[];
  reasoning: string;
  confidence: number;
}

interface UseAutoScannerSelectionReturn {
  selectScanners: (
    repoFullName: string,
    cloneUrl: string,
    repoName: string,
    repoOwner: string,
    customToken?: string,
    branch?: string
  ) => Promise<AutoSelectResult>;
  
  autoScan: (
    repoFullName: string,
    cloneUrl: string,
    repoName: string,
    repoOwner: string,
    customToken?: string,
    runSca?: boolean,
    runSast?: boolean,
    runContainer?: boolean,
    containerImage?: string,
    targets?: string[],
    branch?: string,
    scanMode?: 'fast' | 'standard' | 'deep'
  ) => Promise<AutoScanResult>;
  
  analyzeProject: (projectPath: string) => Promise<AnalyzeResult>;
  
  loading: boolean;
  error: string | null;
  progress: string;
}

export function useAutoScannerSelection(): UseAutoScannerSelectionReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState('');
  
  const selectScanners = async (
    repoFullName: string,
    cloneUrl: string,
    repoName: string,
    repoOwner: string,
    customToken?: string,
    branch?: string
  ): Promise<AutoSelectResult> => {
    setLoading(true);
    setError(null);
    setProgress('Analyzing project structure...');
    
    try {
      const response = await api.post(
        endpoints.scanner.autoSelect,
        {
          repo_full_name: repoFullName,
          clone_url: cloneUrl,
          repo_name: repoName,
          repo_owner: repoOwner,
          custom_token: customToken,
          branch: branch,
        }
      );
      
      setProgress('');
      return response.data;
    } catch (err: any) {
      console.error('Error in selectScanners:', err);
      const errorMsg = err.response?.data?.error || 'Failed to select scanners';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  };
  
  const autoScan = async (
    repoFullName: string,
    cloneUrl: string,
    repoName: string,
    repoOwner: string,
    customToken?: string,
    runSca: boolean = false,
    runSast: boolean = true,
    runContainer: boolean = false,
    containerImage: string = '',
    targets: string[] = [],
    branch?: string,
    scanMode: 'fast' | 'standard' | 'deep' = 'standard'
  ): Promise<AutoScanResult> => {
    setLoading(true);
    setError(null);
    setProgress('Analyzing project and starting scans...');
    
    try {
      const response = await api.post(
        endpoints.scanner.autoScan,
        {
          repo_full_name: repoFullName,
          clone_url: cloneUrl,
          repo_name: repoName,
          repo_owner: repoOwner,
          custom_token: customToken,
          scan_mode: scanMode,
          run_sast: runSast,
          run_sca: runSca,
          run_container: runContainer,
          container_image: containerImage,
          targets: targets,
          branch: branch,
        }
      );
      
      setProgress('');
      return response.data;
    } catch (err: any) {
      console.error('Error in autoScan:', err);
      const errorMsg = err.response?.data?.error || 'Failed to auto-scan';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  };
  
  const analyzeProject = async (projectPath: string): Promise<AnalyzeResult> => {
    setLoading(true);
    setError(null);
    setProgress('Analyzing project...');
    
    try {
      const response = await api.post(
        endpoints.scanner.analyze,
        {
          project_path: projectPath,
        }
      );
      
      setProgress('');
      return response.data;
    } catch (err: any) {
      console.error('Error in analyzeProject:', err);
      const errorMsg = err.response?.data?.error || 'Failed to analyze project';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  };
  
  return {
    selectScanners,
    autoScan,
    analyzeProject,
    loading,
    error,
    progress,
  };
}

export default useAutoScannerSelection;
