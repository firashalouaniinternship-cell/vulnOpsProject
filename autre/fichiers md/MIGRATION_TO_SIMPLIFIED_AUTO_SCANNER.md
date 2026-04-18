# Migration Guide - De l'interface manuelle à l'interface auto-sélectionnée

## 🎯 Guide de migration complet

Comment remplacer votre interface manuelle de sélection des scanners par la nouvelle interface auto-sélectionnée.

## 📋 Étapes de migration

### Étape 1: Sauvegarde (2 min)
```bash
# Faire une sauvegarde de votre code existant
git commit -m "Backup before auto-scanner migration"
git branch backup/manual-scanner-selection
```

### Étape 2: Ajouter les nouveaux fichiers (1 min)
```bash
# Copier les nouveaux composants
cp frontend/src/components/AutoScannerSimplified.tsx frontend/src/components/
cp frontend/src/pages/SimplifiedAnalysisPage.tsx frontend/src/pages/
```

### Étape 3: Remplacer dans votre page d'analyse (5 min)

#### AVANT (Interface manuelle avec tous les boutons):
```tsx
// ancien fichier: frontend/src/pages/AnalysisPage.tsx
export function AnalysisPage() {
  return (
    <div>
      <h1>Security Scanners</h1>
      
      {/* Tous les boutons affichés */}
      <div className="scanner-buttons">
        <button onClick={() => selectScanner('bandit')}>
          🐍 Bandit (Python)
        </button>
        <button onClick={() => selectScanner('eslint')}>
          📝 ESLint (JS/TS)
        </button>
        <button onClick={() => selectScanner('sonarcloud')}>
          ☁️ SonarCloud
        </button>
        {/* ... 7 autres boutons ... */}
      </div>
      
      {/* Résultats */}
      <div>Results...</div>
    </div>
  );
}
```

#### APRÈS (Interface auto-sélectionnée - UN seul bouton):
```tsx
import AutoScannerSimplified from '@/components/AutoScannerSimplified';

export function AnalysisPage() {
  const repo = useParams(); // ou récupérer de votre state
  
  return (
    <div>
      <h1>Security Analysis</h1>
      
      {/* REMPLACE tous les boutons par ce composant */}
      <AutoScannerSimplified
        repoFullName={repo.full_name}
        cloneUrl={repo.clone_url}
        repoName={repo.name}
        repoOwner={repo.owner}
        onAnalysisComplete={(data) => {
          console.log('Scan complete:', data);
        }}
      />
    </div>
  );
}
```

### Étape 4: Mettre à jour les imports (2 min)

```tsx
// ❌ SUPPRIMER ces imports (non utilisés)
// import { useState } from 'react';
// import { useEffect } from 'react';
// import ScannerButton from '@/components/ScannerButton';

// ✅ AJOUTER cet import
import AutoScannerSimplified from '@/components/AutoScannerSimplified';
```

### Étape 5: Supprimer le code obsolète (3 min)

```tsx
// ❌ SUPPRIMER ces fonctions/states (non utilisés):

// Ancien state pour sélection manuelle
const [selectedScanner, setSelectedScanner] = useState(null);
const [showOptions, setShowOptions] = useState(false);

// Ancien handler pour choix manuel
const handleScannerSelect = (scanner) => {
  setSelectedScanner(scanner);
  launchScan(scanner);
};

// ❌ SUPPRIMER les anciens boutons
<div className="scanner-buttons">
  <button onClick={() => handleScannerSelect('bandit')}>
    🐍 Bandit (Python)
  </button>
  {/* ... tous les autres boutons ... */}
</div>
```

### Étape 6: Tester (5 min)

```bash
# Démarrer le dev server
npm run dev

# Tester avec un repo
# 1. Naviguer vers la page d'analyse
# 2. Voir si le bon scanner est auto-détecté
# 3. Cliquer sur le bouton
# 4. Vérifier que les scans lancent
```

## 📊 Before/After Comparison

### AVANT (Code existant)
```tsx
// AnalysisPage.tsx - Avant
import React, { useState } from 'react';

export function AnalysisPage({ repo }) {
  const [selectedScanner, setSelectedScanner] = useState(null);
  
  const handleScannerSelect = (scanner) => {
    setSelectedScanner(scanner);
    // Lancer le scan
    triggerScan(repo, scanner);
  };
  
  return (
    <div>
      <h1>Choose a Scanner</h1>
      
      < className="scanner-selection">
        <button onClick={() => handleScannerSelect('bandit')}>
          🐍 Bandit (Python)
        </button>
        <button onClick={() => handleScannerSelect('eslint')}>
          📝 ESLint (JS/TS)
        </button>
        <button onClick={() => handleScannerSelect('sonarcloud')}>
          ☁️ SonarCloud
        </button>
        <button onClick={() => handleScannerSelect('semgrep')}>
          🔍 Semgrep
        </button>
        <button onClick={() => handleScannerSelect('cppcheck')}>
          ⚙️ Cppcheck
        </button>
        <button onClick={() => handleScannerSelect('gosec')}>
          🔐 Gosec
        </button>
        <button onClick={() => handleScannerSelect('psalm')}>
          ✨ Psalm
        </button>
        <button onClick={() => handleScannerSelect('brakeman')}>
          🛡️ Brakeman
        </button>
        <button onClick={() => handleScannerSelect('clippy')}>
          🦀 Clippy
        </button>
        <button onClick={() => handleScannerSelect('detekt')}>
          🎯 Detekt
        </button>
      </div>
      
      {selectedScanner && <Results scanner={selectedScanner} />}
    </div>
  );
}
```

**Problèmes avec AVANT:**
- ❌ 10+ boutons affichés toujours
- ❌ L'utilisateur doit choisir manuellement
- ❌ Pas de détection automatique
- ❌ UI encombrée

### APRÈS (Nouveau code)
```tsx
// AnalysisPage.tsx - Après
import React from 'react';
import AutoScannerSimplified from '@/components/AutoScannerSimplified';

export function AnalysisPage({ repo }) {
  return (
    <div>
      <h1>Security Analysis</h1>
      
      <AutoScannerSimplified
        repoFullName={repo.full_name}
        cloneUrl={repo.clone_url}
        repoName={repo.name}
        repoOwner={repo.owner}
      />
    </div>
  );
}
```

**Avantages APRÈS:**
- ✅ 1 seul bouton affiché
- ✅ Auto-détection automatique
- ✅ Pas d'interaction utilisateur
- ✅ UI simple et claire
- ✅ Utilise LLM pour sélection intelligente

## 🔄 Intégration progressive

Si vous ne voulez pas remplacer complètement:

### Option 1: Afficher les deux
```tsx
export function AnalysisPage({ repo }) {
  return (
    <div>
      <h1>Security Analysis</h1>
      
      {/* Nouveau: Auto-sélectionné */}
      <section>
        <h2>🤖 Recommended Scanner</h2>
        <AutoScannerSimplified repo={repo} />
      </section>
      
      {/* Ancien: Sélection manuelle (pour backward compatibility) */}
      <section>
        <h2>Manual Scanner Selection</h2>
        <ManualScannerSelection repo={repo} />
      </section>
    </div>
  );
}
```

### Option 2: Toggle entre les deux
```tsx
export function AnalysisPage({ repo }) {
  const [useAuto, setUseAuto] = useState(true);
  
  return (
    <div>
      <div className="toggle">
        <input
          type="checkbox"
          checked={useAuto}
          onChange={(e) => setUseAuto(e.target.checked)}
        />
        <label>Use Auto-Selection</label>
      </div>
      
      {useAuto ? (
        <AutoScannerSimplified repo={repo} />
      ) : (
        <ManualScannerSelection repo={repo} />
      )}
    </div>
  );
}
```

## 📱 Adapter votre UI existante

### Si vous avez une barre de navigation:
```tsx
// NavigationBar.tsx
<nav>
  <Link to="/analysis-auto">🤖 Auto Analysis</Link>
  <Link to="/analysis-manual">⚙️ Manual Selection</Link>
</nav>
```

### Si vous avez un router:
```tsx
// App.tsx ou Router.tsx
<Routes>
  {/* Nouveau */}
  <Route path="/analysis/auto" element={<SimplifiedAnalysisPage />} />
  
  {/* Ancien (gardé pour backward compatibility) */}
  <Route path="/analysis/manual" element={<AnalysisPage />} />
</Routes>
```

## 🗑️ Nettoyer le code obsolète

Après migration, vous pouvez supprimer:
```typescript
// ❌ Supprimer ces fichiers/fonctions:
- components/ScannerButton.tsx (ancien)
- components/ScannerSelection.tsx (ancien)
- hooks/useScannerSelection.ts (ancien)
- utils/scannerLogic.ts (obsolète)

// ✅ Garder:
- components/AutoScannerSimplified.tsx (nouveau)
- hooks/useAutoScannerSelection.ts (nouveau)
- pages/SimplifiedAnalysisPage.tsx (nouveau)
```

## 🧪 Checklist de test post-migration

- [ ] Page charge sans erreurs
- [ ] Spinner s'affiche pendant la détection
- [ ] Bon scanner est auto-détecté
- [ ] Bouton du scanner s'affiche
- [ ] Clic sur le bouton lance le scan
- [ ] Résultats s'affichent correctement
- [ ] Pas d'erreurs dans la console
- [ ] Works on mobile
- [ ] Works on different repos
- [ ] Error handling fonctionne

## 🎨 Personnaliser l'apparence

### Changer la couleur du composant:
```tsx
<AutoScannerSimplified
  repo={repo}
  className="custom-themed"
/>
```

```css
/* Votre CSS */
.custom-themed .scanner-button {
  border-color: #my-color;
}
```

### Changer la taille:
```tsx
<div style={{ maxWidth: '400px' }}>
  <AutoScannerSimplified repo={repo} />
</div>
```

## 🔗 Ressources utiles

- [AutoScannerSimplified Doc](./SIMPLIFIED_AUTO_SCANNER_GUIDE.md)
- [Auto-Scanner Selection Main Doc](./AUTO_SCANNER_SELECTION.md)
- [Quick Setup Guide](./QUICK_SETUP_AUTO_SCANNER.md)

## 🎯 Déploiement progressif

### Phase 1: Développement
```bash
# Branche de feature
git checkout -b feature/auto-scanner-simplified
# Test localement
npm run dev
```

### Phase 2: Testing
```bash
# Push vers staging
git push origin feature/auto-scanner-simplified
# Tester sur staging
```

### Phase 3: Production
```bash
# Merge vers main
git checkout main
git merge feature/auto-scanner-simplified
# Deploy
npm run build && npm run deploy
```

## 💡 Tips & Best Practices

1. **Gardez l'ancienne interface:** Au moins pendant 1 mois pour fallback
2. **Moniteurez les erreurs:** Tracez les auto-détections qui échouent
3. **Collectez des logs:** Sachez quels scanners sont choisis
4. **Demandez du feedback:** À vos utilisateurs sur la nouvelle UX
5. **Optimisez la performance:** Cache les résultats si possible

## ❌ Erreurs courantes à éviter

- ❌ Ne pas garder les imports du ancien code
- ❌ Ne pas tester sur plusieurs types de repos
- ❌ Ne pas mettre à jour les routes si vous avez un router
- ❌ Ne pas oublier d'ajouter les env vars
- ❌ Ne pas déployer sans tester en staging

## 📞 Support

Si vous avez des problèmes:

1. Vérifiez la console pour les erreurs
2. Run `python validate_auto_scanner_setup.py` sur le backend
3. Vérifiez que `OPENROUTER_API_KEY` est configurée
4. Consultez les sectiontroubleshooting du guide principal

---

**Temps total de migration: ~30 minutes** ⏱️

Prêt à migrer? Commencez par l'étape 1! 🚀
