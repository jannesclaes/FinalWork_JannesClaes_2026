# F1 OSC Bridge (FinalWork_JannesClaes_2026)

Dit project is ontwikkeld als onderdeel van de eindopdracht (Final Work 2026) door Jannes Claes. Het betreft een robuust **F1-race playback systeem** dat historische en live Formule 1-data ophaalt via de `fastf1` bibliotheek, deze verwerkt met een virtuele raceklok, en de resulterende telemetrie- en tijdsdata via het OSC (Open Sound Control) protocol streamt naar visuele software zoals **TouchDesigner**.

## ✨ Features

*   **FastF1 Data Engine:** Ophalen en cachen van Formule 1 sessiedata (telemetrie, laptimes, pitstops).
*   **Virtual Race Clock:** Nauwkeurige besturing van de afspeelsnelheid, pauzeren en hervatten van race-data.
*   **OSC Streaming:** Real-time UDP/OSC streaming (standaard poort `7001`) voor naadloze integratie met TouchDesigner of andere software.
*   **AI Commentator (LLM):** Genereert automatische context en commentaar op basis van veranderingen in de race (leiderwissels, status updates).
*   **Dockerized Environment:** Eenvoudig op te zetten en te draaien dankzij de meegeleverde Docker-configuratie.

## 🛠 Prerequisites

*   [Docker & Docker Compose](https://www.docker.com/) (Aanbevolen)
*   **Of lokaal:** Python 3.9+
*   [TouchDesigner](https://derivative.ca/) (of een andere applicatie die OSC kan ontvangen)

## 🚀 Installatie & Setup

### Via Docker (Aanbevolen)

1. Clone deze repository:
   ```bash
   git clone https://github.com/JouwUsername/FinalWork_JannesClaes_2026.git
   cd FinalWork_JannesClaes_2026
   ```

2. Bouw en start de container op de achtergrond:
   ```bash
   docker-compose up -d --build
   ```

3. Om de output van de applicatie (zoals de logs) te bekijken:
   ```bash
   docker-compose logs -f
   ```

4. Om de container weer te stoppen:
   ```bash
   docker-compose down
   ```

### Lokale Installatie

1. Maak een virtual environment aan en activeer deze:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Op Windows: venv\Scripts\activate
   ```
2. Installeer de vereisten:
   ```bash
   pip install -r requirements.txt
   ```
3. Start de applicatie:
   ```bash
   python app.py
   ```

## 🎮 Gebruik & Configuratie

Zodra de applicatie draait, kun je deze besturen via de terminal (of door commando's naar de container te sturen):
*   Typ `start` om de race-playback te beginnen.
*   Typ `pause` om de playback te pauzeren.
*   Typ `quit` om de applicatie af te sluiten.

De applicatie verstuurt standaard OSC-data naar `127.0.0.1` op poort `7001`. Zorg ervoor dat je OSC-In instellingen in TouchDesigner overeenkomen.

### De Race / Sessie Wijzigen

Momenteel staat de sessie geconfigureerd in de broncode. Om een andere race af te spelen, open je `app.py` in een teksteditor, scroll je helemaal naar beneden en pas je de argumenten van de `PlaybackEngine` aan:

```python
if __name__ == "__main__":
    # Verander hier de 'year', 'round' (race nummer) en 'session_type' ('R' voor Race, 'Q' voor Qualifying, etc.)
    engine = PlaybackEngine(year=2026, round=4, session_type='R', speed=1.0, tick_rate=1.0)
    engine.setup()
    engine.run()
```
*Opmerking: Als je wijzigingen in de code aanbrengt en Docker gebruikt, moet je de container opnieuw bouwen met `docker-compose up -d --build`.*

## 🤝 Contributing

We verwelkomen bijdragen aan dit project! Lees onze [Contributing Guidelines](CONTRIBUTING.md) en [Coding Standards](STANDARDS.md) om te zien hoe je kunt helpen. 

Zorg er tevens voor dat je onze [Code of Conduct](CODE_OF_CONDUCT.md) respecteert in alle communicatie en bijdragen.

## 📚 Bronnen en AI-assistentie

Dit project is tot stand gekomen met ondersteuning van AI voor code-optimalisatie en architectuur. De volledige conversaties zijn terug te vinden in de map `sources/`.

### Bibliografie
*   **Claes, J. & Gemini AI.** (2026, 5 mei). *Conversatie over de ontwikkeling van een F1-OSC Bridge* [Chat-logboek]. Gegenereerd via Gemini CLI. Beschikbaar in `sources/chat_f1_project.md`.

### Handige Links
*   [Concept Link 1](https://opncd.ai/share/O7aYxpFa)
*   [Concept Link 2](https://opncd.ai/share/bsCnosMA)

## 📄 License

Dit project is gelicentieerd onder de MIT License - zie het [LICENSE](LICENSE) bestand voor details.
