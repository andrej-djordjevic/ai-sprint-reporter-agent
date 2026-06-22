# Chat Risk Agent

AI agent za automatizovanu analizu rizika u projektima razvoja chat aplikacija, zasnovan na MSF (Microsoft Solutions Framework) metodologiji upravljanja rizicima, LangGraph workflow engine-u i Ollama lokalnim LLM modelima.

Razvijeno u okviru predmeta **Upravljanje rizikom** — Grupa III: Razvoj AI agenta.

**Autori:** Andrej Đorđević (2022/0077), Maša Stevanović (2022/0030), Luka Simić (2022/0020)

---

## Opis projekta

Agent prima tekstualni opis chat projekta (SRS dokument, opis arhitekture, user stories) i kroz višekoračni LangGraph workflow:

1. **Identifikuje** rizike specifične za chat sisteme (WebSocket, autentikacija, enkripcija, GDPR, skalabilnost)
2. **Kategorizuje** ih po 8 MSF kategorija (Scheduling, Budgeting, Staffing, Process, Technology, External, Security, Quality)
3. **Procenjuje** verovatnoću i uticaj svakog rizika (1-5) i računa exposure score
4. **Prioritizuje** top-10 rizika
5. **Generiše** konkretan akcioni plan za ublažavanje
6. **Izvozi** strukturisan izveštaj u Markdown i JSON formatu

Agent nije klasičan chatbot — radi se o sistemu sa definisanim ulazom, višekoračnim workflow-om (LangGraph state machine), LLM komponentom i strukturisanim izlazom.

---

## Arhitektura

```
chat-risk-agent/
├── main.py                  # Ulazna tačka (CLI)
├── agent/
│   ├── graph.py              # LangGraph StateGraph definicija
│   ├── nodes.py               # Čvorovi grafa: identify, assess, prioritize, generate_actions
│   ├── prompts.py             # Strukturisani promptovi (system prompt + ograničenja)
│   └── models.py              # Ollama LLM provider (multi-model podrška)
├── data/
│   ├── loader.py               # Učitavanje teksta (terminal) i fajlova (.txt, .md)
│   └── preprocessor.py         # Čišćenje teksta i chunking
├── output/
│   ├── formatter.py            # Markdown i JSON formatiranje
│   ├── exporter.py             # Zapis na disk
│   └── reports/                # Generisani izveštaji (kreira se automatski)
├── tests/
│   └── test_agent.py           # Unit i integration testovi (3 testna primera)
├── .env.example
├── requirements.txt
└── README.md
```

### LangGraph workflow

```
identify_risks → assess_risks → prioritize → generate_actions → END
```

Svaki čvor je opisan u `agent/nodes.py`. Prvi, drugi i četvrti čvor koriste LLM (Ollama); treći čvor (`prioritize`) je čisto algoritamska obrada (sortiranje po exposure score-u).

---

## Instalacija

### 1. Preduslovi

- Python 3.11+
- [Ollama](https://ollama.ai) instaliran i pokrenut lokalno

### 2. Instalacija Ollama modela

```bash
ollama pull llama3.2
# opciono i drugi modeli:
ollama pull mistral:7b
ollama pull codellama:13b
```

### 3. Pokretanje Ollama servisa

```bash
ollama serve
```

### 4. Kloniranje repozitorijuma i instalacija zavisnosti

```bash
git clone <repo-url>
cd chat-risk-agent
pip install -r requirements.txt
```

### 5. Konfiguracija environment varijabli

```bash
cp .env.example .env
```

Po potrebi izmenite `.env`:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=120
```

---

## Korišćenje

### Interaktivni unos teksta (terminal)

```bash
python main.py
```

Unesite opis projekta, zatim pritisnite `Ctrl+D` (Linux/Mac) ili `Ctrl+Z` + Enter (Windows) za kraj unosa.

### Učitavanje iz fajla

```bash
python main.py --file primer_projekta.txt
```

### Izbor LLM modela

```bash
python main.py --file primer_projekta.txt --model mistral:7b
```

### Primer izlaza u terminalu

```
======================================================================
TOP 5 PRIORITETNIH RIZIKA:
======================================================================
1. [HIGH] Nedostatak end-to-end enkripcije poruka (Score: 20)
2. [HIGH] Nestabilnost WebSocket konekcije pod opterećenjem (Score: 16)
3. [MEDIUM] Nedovoljno iskustvo tima sa real-time arhitekturom (Score: 12)
4. [MEDIUM] Kašnjenje GDPR usaglašenosti (Score: 10)
5. [LOW] Nepotpuna dokumentacija API-ja (Score: 6)
```

Generisani izveštaji se čuvaju u `output/reports/risk_report.md` i `output/reports/risk_report.json`.

---

## Testiranje

```bash
# Unit testovi (ne zahtevaju Ollama)
pytest tests/test_agent.py -v

# Integration testovi sa 3 realna primera (zahtevaju pokrenut Ollama servis)
pytest tests/test_agent.py -v -k "integration or Integration"
```

Projekat je testiran na **3 različita primera** ulaznih podataka:
1. Interna chat aplikacija za mali tim (50 korisnika)
2. Javna chat aplikacija sa visokim opterećenjem (50.000 korisnika, GDPR)
3. Customer support chat widget integrisan u B2B SaaS proizvod

---

## Korišćene tehnologije

| Tehnologija | Namena |
|---|---|
| Python 3.11+ | Programski jezik |
| LangChain / LangGraph | Workflow orkestracija i LLM abstraction |
| Ollama | Lokalni LLM server (llama3.2, mistral, codellama) |
| python-dotenv | Upravljanje environment varijablama |
| pytest | Testiranje |

---

## Ograničenja

- Agent analizira isključivo tekstualne opise projekta, ne analizira stvarni izvorni kod
- Kvalitet analize zavisi od detaljnosti ulaznog dokumenta
- PDF format nije podržan u v1.0 (samo `.txt` i `.md`)
- Maksimalna veličina ulaznog fajla: 500 KB
- Agent nema memoriju između sesija — svaka analiza je nezavisna

## Rizici korišćenja

- LLM može generisati rizike koji nisu potpuno relevantni za specifičan kontekst (halucinacije) — preporučuje se manuelna validacija top rizika pre donošenja odluka
- Tačnost zavisi od izabranog modela; manji modeli (llama3.2:3b) su brži ali manje precizni od većih (mistral:7b, llama3.1:8b)

## Mogućnosti za unapređenje

- Podrška za PDF ulazne dokumente
- Automatska integracija sa JIRA API-jem za kreiranje zadataka od top rizika
- Web/grafički korisnički interfejs
- Praćenje promene rizika kroz vreme (poređenje verzija SRS dokumenta)
