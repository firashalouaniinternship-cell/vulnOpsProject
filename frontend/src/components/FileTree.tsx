import React, { useState } from 'react';
import { ChevronRight, ChevronDown, FileCode, Folder, File } from 'lucide-react';

interface FileNode {
  name: string;
  path: string;
  type: 'blob' | 'tree';
  children?: FileNode[] | null;
}

interface FileTreeProps {
  tree: FileNode[];
  onFileSelect?: (path: string) => void;
}

const FileTreeItem: React.FC<{ node: FileNode; level: number; onFileSelect?: (path: string) => void }> = ({ node, level, onFileSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isFolder = node.type === 'tree';

  const handleClick = () => {
    if (isFolder) {
      setIsOpen(!isOpen);
    } else if (onFileSelect) {
      onFileSelect(node.path);
    }
  };

  const getIcon = () => {
    if (isFolder) {
      return isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />;
    }
    const ext = node.name.split('.').pop()?.toLowerCase();
    if (ext === 'py') return <FileCode size={14} color="#3572A5" />;
    if (['js', 'ts', 'jsx', 'tsx'].includes(ext || '')) return <FileCode size={14} color="#f7df1e" />;
    return <File size={14} color="var(--text-dim)" />;
  };

  return (
    <div>
      <div 
        className="tree-item"
        onClick={handleClick}
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          padding: '6px 8px', 
          paddingLeft: `${level * 16 + 8}px`,
          cursor: 'pointer',
          borderRadius: '4px',
          fontSize: '14px',
          color: isFolder ? 'var(--text-main)' : 'var(--text-dim)',
          transition: 'background 0.2s',
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{ width: '16px', display: 'flex', justifyContent: 'center' }}>
          {isFolder ? (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : null}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isFolder ? <Folder size={14} color="var(--primary)" /> : getIcon()}
          {node.name}
        </span>
      </div>

      {isFolder && isOpen && node.children && (
        <div>
          {node.children.map((child, idx) => (
            <FileTreeItem key={idx} node={child} level={level + 1} onFileSelect={onFileSelect} />
          ))}
        </div>
      )}
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({ tree, onFileSelect }) => {
  return (
    <div className="tree-container">
      {tree.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-dim)', fontSize: '14px' }}>
          Aucun fichier trouvé.
        </div>
      ) : (
        tree.map((node, idx) => (
          <FileTreeItem key={idx} node={node} level={0} onFileSelect={onFileSelect} />
        ))
      )}
    </div>
  );
};

export default FileTree;
