#!/usr/bin/env bash
# =============================================================================
# SKRYPT REORGANIZACJI REPO - Kuchnie na Wymiar (Wrocław 2026)
# =============================================================================
# Uruchom z GŁÓWNEGO katalogu repo (tam gdzie jest README.md)
# Przed uruchomieniem: git status (upewnij się że nie masz niezapisanych zmian)
# Użycie: bash reorganize.sh
# =============================================================================

set -e  # Zatrzymaj skrypt przy pierwszym błędzie

echo "=== START REORGANIZACJI REPO ==="
echo ""

# -----------------------------------------------------------------------------
# KROK 1: Utwórz nowe katalogi
# -----------------------------------------------------------------------------
echo "[1/6] Tworzenie nowych katalogów..."

mkdir -p 00_Dokumenty_Strategiczne
mkdir -p 06_Realizacje
mkdir -p 07_SOP_Montaz/img
mkdir -p 08_Szkolenia_Corpus/img

echo "      OK"

# -----------------------------------------------------------------------------
# KROK 2: Przenieś pliki strategiczne z roota do 00_Dokumenty_Strategiczne/
# -----------------------------------------------------------------------------
echo "[2/6] Przenoszenie dokumentów strategicznych z roota..."

git mv FLOWCHART_Proces_Kompletny.md   00_Dokumenty_Strategiczne/Flowchart_Proces_Kompletny.md
git mv PLAYBOOK_SYSTEM.md              00_Dokumenty_Strategiczne/Playbook_System.md
git mv 00_Podsumowanie_Strategii.md    00_Dokumenty_Strategiczne/Podsumowanie_Strategii.md
git mv 00_Standardy_Materialowe.md     00_Dokumenty_Strategiczne/Standardy_Materialowe.md

echo "      OK"

# -----------------------------------------------------------------------------
# KROK 3: Przenieś SOP-vertical/ -> 07_SOP_Montaz/
# Uwaga: git mv katalogu przenosi całą zawartość z zachowaniem historii
# -----------------------------------------------------------------------------
echo "[3/6] Przemianowanie SOP-vertical/ -> 07_SOP_Montaz/..."

# Przenieś wszystkie pliki z SOP-vertical/ do 07_SOP_Montaz/
# (git mv na katalog działa rekurencyjnie)
git mv SOP-vertical/index.html                      07_SOP_Montaz/index.html
git mv SOP-vertical/common.css                      07_SOP_Montaz/common.css
git mv SOP-vertical/etap-1-strategia-projekt.html   07_SOP_Montaz/etap-1-strategia-projekt.html
git mv SOP-vertical/etap-1-1-karta-pomiarowa.html   07_SOP_Montaz/etap-1-1-karta-pomiarowa.html

# Przenieś pozostałe etap-*.html jeśli istnieją
for f in SOP-vertical/etap-*.html; do
    [ -f "$f" ] && git mv "$f" "07_SOP_Montaz/$(basename $f)"
done

# Przenieś 1.1.B.jpg do img/ (nie był referowany w HTML - bezpieczne)
git mv SOP-vertical/1.1.B.jpg  07_SOP_Montaz/img/1.1.B.jpg

# Przenieś zawartość SOP-vertical/img/ do 07_SOP_Montaz/img/
if [ -d "SOP-vertical/img" ]; then
    for f in SOP-vertical/img/*; do
        [ -f "$f" ] && git mv "$f" "07_SOP_Montaz/img/$(basename $f)"
    done
fi

# Przenieś pozostałe luźne pliki z SOP-vertical/ (MD, inne)
for f in SOP-vertical/*.md; do
    [ -f "$f" ] && git mv "$f" "07_SOP_Montaz/$(basename $f)"
done

# Usuń pusty katalog (git nie śledzi katalogów, ale dla porządku)
if [ -d "SOP-vertical" ] && [ -z "$(ls -A SOP-vertical)" ]; then
    rmdir SOP-vertical
fi

echo "      OK"

# -----------------------------------------------------------------------------
# KROK 4: Przenieś corpus-filmy/ i corpus-kuchnia-kroki.md -> 08_Szkolenia_Corpus/
# -----------------------------------------------------------------------------
echo "[4/6] Przenoszenie materiałów szkoleniowych Corpus..."

git mv corpus-kuchnia-kroki.md  08_Szkolenia_Corpus/kuchnia-kroki.md

if [ -d "corpus-filmy" ]; then
    for f in corpus-filmy/*; do
        if [ -f "$f" ]; then
            # Obrazy PNG/JPG idą do img/
            case "$f" in
                *.png|*.jpg|*.jpeg)
                    git mv "$f" "08_Szkolenia_Corpus/img/$(basename $f)"
                    ;;
                *)
                    git mv "$f" "08_Szkolenia_Corpus/$(basename $f)"
                    ;;
            esac
        fi
    done
    # Usuń pusty katalog
    if [ -z "$(ls -A corpus-filmy)" ]; then
        rmdir corpus-filmy
    fi
fi

echo "      OK"

# -----------------------------------------------------------------------------
# KROK 5: Przenieś pomiar-kuchnia1/ -> 06_Realizacje/
# -----------------------------------------------------------------------------
echo "[5/6] Przenoszenie realizacji..."

if [ -d "02_Projektowanie_i_Style/pomiar-kuchnia1" ]; then
    mkdir -p 06_Realizacje/pomiar-kuchnia1
    for f in 02_Projektowanie_i_Style/pomiar-kuchnia1/*; do
        [ -f "$f" ] && git mv "$f" "06_Realizacje/pomiar-kuchnia1/$(basename $f)"
    done
    if [ -z "$(ls -A 02_Projektowanie_i_Style/pomiar-kuchnia1)" ]; then
        rmdir 02_Projektowanie_i_Style/pomiar-kuchnia1
    fi
fi

echo "      OK"

# -----------------------------------------------------------------------------
# KROK 6: Przenieś luźne obrazy z 03_Materialy_i_Katalogi/ do Sciagi_i_Wzorniki/
# -----------------------------------------------------------------------------
echo "[6/6] Porządkowanie luźnych obrazów w 03_Materialy_i_Katalogi/..."

mkdir -p 03_Materialy_i_Katalogi/Sciagi_i_Wzorniki

for f in 03_Materialy_i_Katalogi/*.png 03_Materialy_i_Katalogi/*.jpg 03_Materialy_i_Katalogi/*.jpeg; do
    [ -f "$f" ] && git mv "$f" "03_Materialy_i_Katalogi/Sciagi_i_Wzorniki/$(basename $f)"
done

echo "      OK"

# -----------------------------------------------------------------------------
# PODSUMOWANIE
# -----------------------------------------------------------------------------
echo ""
echo "=== REORGANIZACJA ZAKOŃCZONA ==="
echo ""
echo "Następne kroki:"
echo "  1. Sprawdź zmiany:  git status"
echo "  2. Przejrzyj diff:  git diff --cached --stat"
echo "  3. Zatwierdź:       git commit -m 'refactor: reorganizacja struktury repo'"
echo ""
echo "Nowa struktura:"
echo "  00_Dokumenty_Strategiczne/  <- pliki strategiczne z roota"
echo "  06_Realizacje/              <- pomiary i zdjęcia z realizacji"
echo "  07_SOP_Montaz/              <- była SOP-vertical/"
echo "  08_Szkolenia_Corpus/        <- był corpus-filmy/ + corpus-kuchnia-kroki.md"
echo ""
echo "UWAGA: Ścieżki wewnątrz plików HTML nie wymagały zmian"
echo "       (wszystkie linki były relatywne i pozostają poprawne)"
