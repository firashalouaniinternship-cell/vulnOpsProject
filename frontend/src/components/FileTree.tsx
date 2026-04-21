import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, FileCode, Folder, File, CheckSquare, Square, MinusSquare } from 'lucide-react';

interface FileNode {
  name: string;
  path: string;
  type: 'blob' | 'tree';
  children?: FileNode[] | null;
}

interface FileTreeProps {
  tree: FileNode[];
  selectedPaths: Set<string>;
  onSelectionChange: (paths: Set<string>) => void;
}

const FileTreeItem: React.FC<{ 
  node: FileNode; 
  level: number; 
  selectedPaths: Set<string>;
  onToggle: (path: string, isFolder: boolean) => void;
}> = ({ node, level, selectedPaths, onToggle }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isFolder = node.type === 'tree';
  const isSelected = selectedPaths.has(node.path);

  // Check if any children are selected (for indeterminate state eventually, 
  // but let's see if we can deduce it from selectedPaths)
  const hasSelectedChildren = isFolder && node.children?.some(child => 
    selectedPaths.has(child.path) || (child.type === 'tree' && Array.from(selectedPaths).some(p => p.startsWith(child.path + '/')))
  );

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggle(node.path, isFolder);
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

  const getCheckboxIcon = () => {
    if (isSelected) return <CheckSquare size={16} color="var(--primary)" />;
    if (hasSelectedChildren) return <MinusSquare size={16} color="var(--primary)" style={{ opacity: 0.7 }} />;
    return <Square size={16} color="var(--text-dim)" />;
  };

  return (
    <div>
      <div 
        className="tree-item"
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          padding: '6px 8px', 
          paddingLeft: `${level * 16 + 8}px`,
          cursor: 'pointer',
          borderRadius: '4px',
          fontSize: '13px',
          color: isFolder ? 'var(--text-main)' : 'var(--text-dim)',
          transition: 'background 0.2s',
          background: isSelected ? 'rgba(99, 102, 241, 0.08)' : 'transparent'
        }}
        onClick={() => isFolder && setIsOpen(!isOpen)}
        onMouseEnter={(e) => e.currentTarget.style.background = isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255,255,255,0.05)'}
        onMouseLeave={(e) => e.currentTarget.style.background = isSelected ? 'rgba(99, 102, 241, 0.08)' : 'transparent'}
      >
        <span style={{ width: '16px', display: 'flex', justifyContent: 'center', color: 'var(--text-dim)' }}>
          {isFolder ? (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : null}
        </span>
        
        <div 
          onClick={handleToggle}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          {getCheckboxIcon()}
        </div>

        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isFolder ? <Folder size={14} color="var(--primary)" /> : getIcon()}
          <span style={{ 
            overflow: 'hidden', 
            textOverflow: 'ellipsis', 
            whiteSpace: 'nowrap',
            fontWeight: isSelected ? 600 : 400,
            color: isSelected ? 'white' : 'inherit'
          }}>
            {node.name}
          </span>
        </span>
      </div>

      {isFolder && isOpen && node.children && (
        <div className="tree-children">
          {node.children.map((child, idx) => (
            <FileTreeItem 
              key={`${child.path}-${idx}`} 
              node={child} 
              level={level + 1} 
              selectedPaths={selectedPaths}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({ tree, selectedPaths, onSelectionChange }) => {
  
  // Helper to get all paths in the tree recursively
  const getAllPaths = (nodes: FileNode[], paths: string[] = []) => {
    nodes.forEach(node => {
      paths.push(node.path);
      if (node.children) {
        getAllPaths(node.children, paths);
      }
    });
    return paths;
  };

  const allPaths = getAllPaths(tree);
  const isAllSelected = allPaths.length > 0 && allPaths.every(p => selectedPaths.has(p));
  const isSomeSelected = !isAllSelected && allPaths.some(p => selectedPaths.has(p));

  const handleSelectAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isAllSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(allPaths));
    }
  };

  const handleToggle = (path: string, isFolder: boolean) => {
    const newPaths = new Set(selectedPaths);
    const currentlySelected = newPaths.has(path);

    // Function to find a node by path
    const findNode = (nodes: FileNode[], targetPath: string): FileNode | null => {
      for (const node of nodes) {
        if (node.path === targetPath) return node;
        if (node.children) {
          const found = findNode(node.children, targetPath);
          if (found) return found;
        }
      }
      return null;
    };

    // Helper to get all descendants paths
    const getDescendantPaths = (node: FileNode, paths: string[] = []) => {
      if (node.children) {
        node.children.forEach(child => {
          paths.push(child.path);
          getDescendantPaths(child, paths);
        });
      }
      return paths;
    };

    if (currentlySelected) {
      newPaths.delete(path);
      if (isFolder) {
        const node = findNode(tree, path);
        if (node) {
          const descendants = getDescendantPaths(node);
          descendants.forEach(p => newPaths.delete(p));
        }
      }
    } else {
      newPaths.add(path);
      if (isFolder) {
        const node = findNode(tree, path);
        if (node) {
          const descendants = getDescendantPaths(node);
          descendants.forEach(p => newPaths.add(p));
        }
      }
    }

    onSelectionChange(newPaths);
  };

  return (
    <div className="tree-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {tree.length > 0 && (
        <div 
          onClick={handleSelectAll}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px', 
            padding: '8px 12px', 
            borderBottom: '1px solid var(--border)',
            background: 'rgba(255,255,255,0.02)',
            cursor: 'pointer',
            fontSize: '12px',
            color: 'var(--text-bright)',
            fontWeight: 600,
            transition: 'background 0.2s',
            marginBottom: '4px'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {isAllSelected ? (
              <CheckSquare size={16} color="var(--primary)" />
            ) : isSomeSelected ? (
              <MinusSquare size={16} color="var(--primary)" style={{ opacity: 0.7 }} />
            ) : (
              <Square size={16} color="var(--text-dim)" />
            )}
          </div>
          Tout sélectionner
          <span style={{ fontSize: '10px', color: 'var(--text-dim)', marginLeft: 'auto', background: 'rgba(255,255,255,0.05)', padding: '1px 6px', borderRadius: '10px' }}>
            {selectedPaths.size}
          </span>
        </div>
      )}

      <div style={{ overflowY: 'auto', flex: 1, padding: '4px' }}>
        {tree.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-dim)', fontSize: '14px' }}>
            Aucun fichier trouvé.
          </div>
        ) : (
          tree.map((node, idx) => (
            <FileTreeItem 
              key={`${node.path}-${idx}`} 
              node={node} 
              level={0} 
              selectedPaths={selectedPaths}
              onToggle={handleToggle}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default FileTree;
