@echo off
REM ============================================================
REM  Script de compilation du rapport PFE LaTeX
REM  Necessite une installation LaTeX (MiKTeX ou TeX Live)
REM ============================================================

echo [VulnOps PFE] Compilation du rapport LaTeX...
echo.

REM Premiere passe pdflatex
echo [1/4] Premiere passe pdflatex...
pdflatex -interaction=nonstopmode rapport_pfe.tex
if %ERRORLEVEL% NEQ 0 (
    echo ERREUR lors de la premiere passe. Verifiez les logs.
    pause
    exit /b 1
)

REM Compilation de la bibliographie (bibtex)
echo [2/4] Compilation de la bibliographie...
bibtex rapport_pfe
if %ERRORLEVEL% NEQ 0 (
    echo ATTENTION : BibTeX n'a pas trouve de references.
)

REM Deuxieme passe pdflatex (pour les references)
echo [3/4] Deuxieme passe pdflatex...
pdflatex -interaction=nonstopmode rapport_pfe.tex

REM Troisieme passe pdflatex (pour la table des matieres)
echo [4/4] Troisieme passe pdflatex...
pdflatex -interaction=nonstopmode rapport_pfe.tex

echo.
echo [OK] Compilation terminee ! Le fichier rapport_pfe.pdf a ete genere.
echo.

REM Optionnel : ouvrir le PDF
start rapport_pfe.pdf

pause
