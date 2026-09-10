---
name: mega-card
description: Karta w stylu FIFA/FUT plus 24-ramienna pajęczyna umiejętności z raportu MEGA Assessment (mega-assessment-*.md). Generuje HTML i PNG, opcjonalnie publikuje jako artifact. Użyj gdy user prosi o kartę zawodnika, pajęczynę, radar albo wykres umiejętności z wyniku MEGA / assessmentu.
---

# MEGA card

Z raportu MEGA Assessment robi grafikę: brązowa/srebrna/złota karta FUT z oceną ogólną i 6 statystykami na sześciokącie, obok pełna pajęczyna 24 cech (0-100).

## Kroki

1. **Znajdź raport.** Ścieżka z argumentu. Brak argumentu: najnowszy `mega-assessment-*.md` w cwd, potem w `~/projects/tmp/`. Nic nie ma: zapytaj o ścieżkę.
2. **Wygeneruj.** Bash z `dangerouslyDisableSandbox: true` - headless Chrome w sandboxie wisi i nie zapisuje zrzutu:
   ```bash
   python3 ~/.claude/skills/mega-card/render.py <raport.md> [--name NAZWISKO] [--out-dir DIR] [--no-png]
   ```
   Domyślnie nazwisko `KRYCH`, pliki lądują obok raportu jako `mega-pajeczyna-<data>.html/.png`. Skrypt kończy się błędem, gdy w raporcie brakuje którejś z T01-T24.
3. **Obejrzyj PNG raz** (Read). Szukaj uciętego tekstu i nachodzących etykiet. Poprawki robisz w `template.html`, nie w wygenerowanym pliku.
4. **Opublikuj** wygenerowany HTML przez Artifact (favicon `🕸️`), chyba że user chce tylko PNG. Podaj link i ścieżkę PNG.

## Jak liczone

- Wynik cechy = `(applied + declined) / eligible * 100`, zaokrąglony. Declined to świadome pominięcie, liczy się na plus.
- Ocena ogólna = średnia z 24 cech. Tier karty: 75+ złoto, 65-74 srebro, poniżej brąz (progi jak w FIFA).
- Kolory punktów: 70+ zielony, 50-69 żółty, poniżej 50 czerwony.
- Grupy (własny podział, MEGA ich nie definiuje):

| Kod | Grupa | Cechy |
|---|---|---|
| INT | Intencja | T01, T02, T05, T06 |
| KTX | Kontekst | T03, T04, T09, T10, T11, T12 |
| DIA | Diagnoza | T07, T08, T13 |
| DEL | Delegacja | T14, T15, T16, T17, T19, T20 |
| STR | Sterowanie | T18, T21, T22 |
| WER | Weryfikacja | T23, T24 |

Zmiana grup albo polskich nazw cech: `GROUPS` i `NAMES` w `template.html`.

## Parsowanie raportu

- Cechy: pierwszy wiersz tabeli `| Txx | Nazwa | eligible | applied | declined | missed | verified |` na każde ID. Wiersze tabeli wskaźników (kebab-case w drugiej kolumnie) są pomijane.
- Stopka karty: `**Data skanu:**`, `Epizody zadaniowe`, `Przeskanowane`, `(N dni)`. Brak pola = pomijane.
