# PRD — KryzIO

## Opis produktu

KryzIO to webowy agent AI dla mieszkańców Krakowa, który zbiera w jednym miejscu dane o zagrożeniach z publicznych źródeł (IMGW, Tauron, GIOŚ, Airly, poradnik bezpieczeństwa, schrony) i na pytanie zadane zwykłym językiem mówi, co dana osoba ma zrobić pod swoim adresem przed zdarzeniem kryzysowym, w trakcie i po nim — jako uzupełnienie państwowego systemu ostrzegania, nie jego zastępstwo.

## Scope

### MVP (robimy na pewno)

- [ ] Czat z agentem jako ekran startowy; pytania zwykłym językiem (F1)
- [ ] Rozpoznawanie miejsca z pytania + geokodowanie; prośba o doprecyzowanie, gdy brak miejsca (F2)
- [ ] Odmowa dla miejsc poza Krakowem: „KryzIO działa na razie tylko na terenie Krakowa” (US-01)
- [ ] Odpowiedź: sytuacja w miejscu + lista kroków przed / w trakcie / po (F3)
- [ ] Źródło i godzina aktualizacji przy każdej odpowiedzi (F4); „Brak danych”, gdy danych nie ma (F5)
- [ ] Szybkie pytania jako przyciski (F6)
- [ ] Opcjonalny skład gospodarstwa (dzieci, senior, zwierzę) uwzględniany w krokach; pamięć tylko w sesji (F6a, F6b)
- [ ] Tryb zagrożenia życia: baner „Dzwoń 112” + kroki z poradnika (US-03)
- [ ] Krótka odmowa pytań spoza tematu (US-02)
- [ ] Stały dopisek: KryzIO nie zastępuje służb (US-05)
- [ ] Zakładka Mapa: podsumowanie zagrożeń (IMGW, stany wód, jakość powietrza, wyłączenia prądu) + mapa Krakowa (F7, F8)
- [ ] Schrony na mapie + najbliższy schron dla adresu (F9)
- [ ] Numery alarmowe i zasady z poradnika dostępne zawsze (F13)
- [ ] Pobieranie danych w tle z cache; Airly co 2h; najświeższe źródło wygrywa; oznaczenie „dane sprzed X godz.” (US-04, US-07)
- [ ] Zakładka Demo (tylko przy `DEMO_MODE`): scenariusze powódź / brak prądu / atak bombowy, baner SYMULACJA, czat działa na danych symulowanych (F10–F12)
- [ ] Duża czcionka i kontrast WCAG AA (US-08)
- [ ] docker-compose (4 kontenery), Makefile, testy, README

### Out of scope (NIE robimy)

- [ ] Powiadomienia push i proaktywne ostrzeżenia
- [ ] Język angielski i inne języki
- [ ] Konta użytkowników, logowanie, zapis rozmów na serwerze
- [ ] Aplikacja mobilna natywna
- [ ] Zgłaszanie zdarzeń przez mieszkańców
- [ ] Panel dla urzędu / służb
- [ ] Własny model predykcji zalania / pożaru (tylko dane ze źródeł)
- [ ] Obszar poza Krakowem
- [ ] Odczyt głosowy i wpisywanie głosem
- [ ] Scenariusz pożaru w Demo
- [ ] Tryb Demo w docelowej aplikacji

## User flows

### Flow 1: Pytanie o zagrożenie pod adresem (na żywo)
Start (Czat) → Marta wpisuje „Czy na Kobierzyńskiej grozi zalanie?” → agent geokoduje adres (Kraków ✓) → agent pobiera ostrzeżenia IMGW, stany wód, poradnik → odpowiedź: sytuacja + kroki przed/w trakcie/po + źródła z godziną + dopisek o służbach → Marta podaje „mam mamę 74 lata” → agent uzupełnia kroki o seniora

**Warianty:**
- Brak miejsca w pytaniu → agent pyta o ulicę / osiedle
- Adres poza Krakowem → komunikat o zasięgu, bez odpowiedzi merytorycznej
- Adres nieznany geokoderowi → prośba o doprecyzowanie
- Brak danych dla danego zagrożenia → „Brak danych” + ogólne wskazówki z poradnika
- Dane starsze niż próg → odpowiedź z wyraźnym „dane sprzed X godz.”
- Źródła sprzeczne → najświeższy odczyt
- Błąd modelu LLM / timeout → komunikat „Agent chwilowo niedostępny” + link do numerów alarmowych i poradnika
- Pytanie spoza tematu → krótka odmowa i powrót do tematu

### Flow 2: Zagrożenie życia teraz
Start (Czat) → Marta pisze „woda wlewa się do piwnicy, mama nie zejdzie” → agent rozpoznaje sytuację „tu i teraz” → na górze odpowiedzi baner „Dzwoń 112” (klikalny `tel:112`) → pod spodem kroki z poradnika dla powodzi → najbliższy schron / bezpieczne miejsce, jeśli znany adres

**Warianty:**
- Typ zdarzenia nierozpoznany → baner 112 + ogólne zasady z poradnika
- Błąd LLM → baner 112 nadal widoczny (fallback po stronie frontu na słowa kluczowe)

### Flow 3: Prezentacja — scenariusz Demo
Prezenter otwiera zakładkę Demo (widoczna przy `DEMO_MODE`) → wybiera scenariusz (powódź / brak prądu / atak bombowy) → baner SYMULACJA, mapa pokazuje symulowane zagrożenia → prezenter zadaje pytanie w czacie → agent odpowiada na danych symulowanych (z oznaczeniem źródła „symulacja”) → atak bombowy: symulowany komunikat + poradnik + najbliższy schron

**Warianty:**
- Przełączenie scenariusza → czat i mapa resetują się do nowego scenariusza
- Wyjście z Demo → powrót do danych na żywo
- `DEMO_MODE` wyłączony → zakładki Demo nie ma, endpointy demo zwracają 404

### Flow 4: Mapa i najbliższy schron
Start → zakładka Mapa → podsumowanie zagrożeń (kafelki) + mapa z warstwami → Marta wpisuje adres → marker adresu + najbliższy schron z odległością

**Warianty:**
- Źródło niedostępne → kafelek z ostatnimi danymi i „dane sprzed X godz.”
- Adres poza Krakowem → komunikat o zasięgu

## User stories + acceptance criteria

### Story 1: Odpowiedź dla mojego adresu
**Jako** mieszkanka **chcę** zapytać o zagrożenie pod moim adresem, **żeby** wiedzieć, co konkretnie zrobić.

**Acceptance criteria:**
- [ ] Odpowiedź zawiera sekcje: sytuacja, przed, w trakcie, po
- [ ] Każda informacja o danych ma źródło i godzinę aktualizacji
- [ ] Agent nie podaje danych, których nie zwróciło żadne narzędzie; przy braku — „Brak danych”
- [ ] Dopisek o nadrzędności służb jest w każdej odpowiedzi merytorycznej
- [ ] Kontekst (adres, skład gospodarstwa) działa w obrębie sesji; odświeżenie strony go czyści

### Story 2: Zasięg Kraków
**Jako** użytkowniczka **chcę** jasno wiedzieć, że pytam o obszar spoza zasięgu, **żeby** nie polegać na pustej odpowiedzi.

**Acceptance criteria:**
- [ ] Adres poza granicami Krakowa → dokładnie komunikat „KryzIO działa na razie tylko na terenie Krakowa”
- [ ] Test jednostkowy: adres w Krakowie → OK, adres w Skawinie → odmowa

### Story 3: Zagrożenie życia
**Jako** osoba w niebezpieczeństwie **chcę** natychmiast zobaczyć, że mam dzwonić na 112, **żeby** nie tracić czasu na czytanie.

**Acceptance criteria:**
- [ ] Baner „Dzwoń 112” na górze odpowiedzi, kontrastowy, z linkiem `tel:112`
- [ ] Pod banerem kroki z poradnika dla rozpoznanego typu zdarzenia
- [ ] Baner pojawia się także przy błędzie LLM (fallback na słowa kluczowe)

### Story 4: Pytanie spoza tematu
**Jako** właściciel systemu **chcę**, żeby agent krótko odmawiał pytań spoza tematu, **żeby** nie marnować tokenów.

**Acceptance criteria:**
- [ ] Odpowiedź off-topic ma maks. 2 zdania i zachęca do pytania o bezpieczeństwo
- [ ] Limit tokenów odpowiedzi ustawiony w konfiguracji agenta

### Story 5: Aktualność danych
**Jako** mieszkanka **chcę** widzieć, jak świeże są dane, **żeby** ocenić, czy im ufać.

**Acceptance criteria:**
- [ ] Przy sprzecznych źródłach pokazywany jest najświeższy odczyt
- [ ] Dane starsze niż 3h oznaczone „dane sprzed X godz.” (czat i mapa)
- [ ] Niedostępne źródło → ostatnie dane z cache z datą; brak cache → „Brak danych”
- [ ] Airly odpytywane nie częściej niż co 2h

### Story 6: Mapa i schron
**Jako** mieszkanka **chcę** zobaczyć zagrożenia na mapie i najbliższy schron, **żeby** wiedzieć, dokąd iść.

**Acceptance criteria:**
- [ ] Mapa Krakowa z warstwami: zagrożenia, schrony
- [ ] Po podaniu adresu — marker i najbliższy schron z odległością
- [ ] Dane schronów pochodzą z pliku JSON z podanym źródłem

### Story 7: Demo na prezentacji
**Jako** prezenter **chcę** uruchomić symulowany scenariusz, **żeby** pokazać jury działanie w realnej sytuacji kryzysowej.

**Acceptance criteria:**
- [ ] Zakładka Demo widoczna tylko przy `DEMO_MODE=true`
- [ ] 3 scenariusze: powódź, brak prądu, atak bombowy
- [ ] Baner SYMULACJA widoczny przez cały czas w Demo
- [ ] Czat w Demo korzysta z danych symulowanych, źródło oznaczone jako „symulacja”

### Story 8: Czytelność
**Jako** senior ze słabym wzrokiem **chcę** dużą czcionkę i dobry kontrast, **żeby** samodzielnie odczytać informacje.

**Acceptance criteria:**
- [ ] Bazowa czcionka min. 18px
- [ ] Kontrast tekstu min. WCAG AA (4.5:1)
- [ ] Interfejs używalny na telefonie (min. 360px szerokości)

## Definition of Done

Produkt jest gotowy, gdy:
- [ ] `make up` uruchamia 4 kontenery lokalnie, aplikacja działa end-to-end
- [ ] `make test` przechodzi (api, agent, frontend)
- [ ] Flow 1–4 działają na danych realnych (lub z cache) i w Demo
- [ ] Wszystkie 3 scenariusze Demo przechodzą bez błędów
- [ ] Frontend na Vercel, backend na VPS (HTTPS), demo dostępne pod publicznym linkiem
- [ ] README: opis, uruchomienie, architektura, źródła danych, ujawnienie AI / API / danych
- [ ] Brak sekretów w repo (`.env` w `.gitignore`)
- [ ] Materiały zgłoszeniowe: tytuł, zespół, opis, PDF ≤ 10 slajdów

## Non-functional requirements

### Bezpieczeństwo / prywatność
- Bez kont; rozmowy i adresy nie są zapisywane na serwerze ani w logach
- Klucze API (GLM, Airly) tylko w `.env`
- CORS backendu ograniczony do domeny frontendu
- Agent korzysta wyłącznie z danych z narzędzi; system prompt zabrania zmyślania danych

### Platforma / dostępność
- Aplikacja webowa, responsywna (telefon i desktop)
- Język polski
- Czcionka bazowa min. 18px, kontrast WCAG AA

### Performance
- Odpowiedź agenta typowo do kilku sekund (zależna od GLM); wskaźnik „agent pisze…”
- Panel Mapa ładuje dane z cache, bez czekania na zewnętrzne źródła

### Poufność
- Projekt jawny, repo publiczne; brak nazw klientów
- Tylko publiczne źródła danych; źródła i licencje wymienione w README
- Dane wrażliwe: adres i treść pytań użytkownika — nie logować, nie commitować przykładowych rozmów z prawdziwymi danymi
- Wyraźne oddzielenie pracy z HackYeah od wcześniejszej (kod dopiero po starcie hackathonu: 3.10, 23:00)

## Otwarte pytania / założenia

| Pytanie | Status | Decyzja |
|---------|--------|---------|
| Próg nieaktualności danych | Założenie | 3h |
| Demo włączane flagą | Założenie | `DEMO_MODE` |
| Pożar w Demo | Założenie | Poza Demo (scenariusze: powódź, brak prądu, atak bombowy) |
| Rozpoznanie „zagrożenia życia” | Założenie | LLM klasyfikuje + fallback słów kluczowych na froncie |
| Czcionka bazowa | Założenie | 18px |
| Off-topic | Założenie | maks. 2 zdania |
| Domena / HTTPS na VPS | Ustalone | Brak HTTPS teraz — zespół skonfiguruje przed wdrożeniem (wymagane przez Vercel) |
| Częstotliwość odświeżania źródeł poza Airly | Ustalone | Co 30 min, z poszanowaniem rate limitów źródeł (Airly co 2h) |
| Z1 fallback 112, Z2 18px / off-topic 2 zdania, Z3 komunikat przy awarii GLM | Zaakceptowane (brak uwag) | Jak w założeniach |
