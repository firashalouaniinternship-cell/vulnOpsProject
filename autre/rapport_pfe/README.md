# Rapport PFE -- VulnOps

> Rapport de Projet de Fin d'Études pour l'obtention du diplôme d'Ingénieur en Informatique  
> Sujet : **VulnOps -- Plateforme DevSecOps Intelligente pour l'Analyse Automatisée des Vulnérabilités**

---

## Structure du répertoire

```
rapport_pfe/
├── rapport_pfe.tex       # Fichier LaTeX principal (rapport complet)
├── figures/              # Images et captures d'écran à insérer
├── compile.bat           # Script de compilation Windows
├── .gitignore            # Fichiers LaTeX à ne pas versionner
└── README.md             # Ce fichier
```

## Prérequis

- **MiKTeX** (Windows) ou **TeX Live** (Linux/Mac)
- Packages LaTeX requis (installés automatiquement avec MiKTeX) :
  - `babel` (french)
  - `graphicx`, `xcolor`, `hyperref`
  - `pgfgantt`, `tikz`
  - `booktabs`, `longtable`, `tabularx`
  - `listings`, `fancyhdr`, `titlesec`
  - `geometry`, `setspace`, `parskip`

## Compilation

### Sous Windows (MiKTeX)
```batch
compile.bat
```
Ou manuellement :
```batch
pdflatex rapport_pfe.tex
bibtex rapport_pfe
pdflatex rapport_pfe.tex
pdflatex rapport_pfe.tex
```

### Sous Linux / Mac (TeX Live)
```bash
pdflatex rapport_pfe.tex
bibtex rapport_pfe
pdflatex rapport_pfe.tex
pdflatex rapport_pfe.tex
```

### Avec latexmk (recommandé)
```bash
latexmk -pdf rapport_pfe.tex
```

## Personnalisation à effectuer

Recherchez et remplacez les éléments entre crochets `[...]` dans le fichier LaTeX :

| Élément | Description |
|---------|-------------|
| `[Votre Université]` | Nom complet de l'université |
| `[Votre Établissement]` | Nom de l'institut/école |
| `[Nom de l'organisme d'accueil]` | Entreprise du stage |
| `[Nom de l'encadrant professionnel]` | Nom de l'encadrant en entreprise |
| `[Date début]` / `[Date fin]` | Période du stage |
| `[durée du stage]` | Ex. : 4 mois |
| `[CPU]`, `[RAM Go]`, `[Windows/Linux]` | Caractéristiques matérielles |
| `[X%]` | Taux de pertinence de la sélection LLM |

## Ajout des figures

Placez vos captures d'écran dans le dossier `figures/` et remplacez les blocs :
```latex
\fbox{\parbox{13cm}{\centering\vspace{3cm}
\textit{[Insérer ici ...]}
\vspace{3cm}}}
```
par :
```latex
\includegraphics[width=\textwidth]{figures/nom_de_votre_image.png}
```

## Conseils de rédaction

- Utiliser **"nous"** à la place de **"je"** (ex. : "Nous présentons...")
- Chaque figure/tableau doit être **interprété** en utilisant sa référence
  (ex. : "Dans la figure 3.1, nous présentons...")
- Les références bibliographiques doivent être citées avec `\cite{ref}`
- Éviter tout copier/coller : reformuler avec vos propres mots
- Les diagrammes sont des **diagrammes UML**

---
*Rapport généré pour le PFE 2025-2026 -- Dr. Selma Belgacem (encadrante)*
