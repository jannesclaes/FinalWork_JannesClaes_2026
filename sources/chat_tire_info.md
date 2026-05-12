## USER 🧑‍💻

oke het volgende wat ik wil doen is in verband met banden informatie, wat ik dus net wil doorkrijgen is per coureur welkje ze aan het gebruiken zijn ( soft, medium, hard) en hoeveel rondes er al op die banden zijn gereden

---

## MODEL ✨

Ik heb de bandeninformatie (compound en het aantal gereden rondes) toegevoegd aan de data engine en de OSC-bridge. 

### Belangrijkste wijzigingen:
1.  **Data Extraction:** Tijdens het inladen van de sessie wordt nu voor elke ronde de `Compound` en de `TyreLife` opgehaald.
2.  **State Tracking:** De `get_state_at` methode bepaalt nu live op welke banden een coureur rijdt op basis van de race-tijd.
3.  **OSC Transmissie:** De informatie wordt verstuurd via `/p{position}/tyre/compound` en `/p{position}/tyre/life`.

---

## USER 🧑‍💻

kan je ipv soft, medium, hard getallen geven: 0, 1, 2

---

## MODEL ✨

Ik heb de compound-informatie aangepast naar gehele getallen (integers) voor een efficiëntere verwerking in je dashboard.

**Mapping:**
*   `0` = SOFT
*   `1` = MEDIUM
*   `2` = HARD
*   `3` = INTERMEDIATE
*   `4` = WET
*   `5` = UNKNOWN

De OSC-berichten sturen nu deze getallen door in plaats van de tekstuele namen.

---

## USER 🧑‍💻

kan je even opnieuw proberen en kijken of het laatste in orde is?oke het werkt, kijk in de map sources en slaag dit gesprek daar op zoals de andere die er in staan
