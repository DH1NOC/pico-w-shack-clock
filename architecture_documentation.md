# 🛠️ Projekt-Architektur: Shack-Weltzeituhr

Diese Dokumentation beschreibt den technischen Aufbau der Firmware für den Raspberry Pi Pico W. Das System ist modular gestaltet, um Hardware-Abhängigkeiten zu kapseln und die Systemstabilität bei Netzwerkausfällen zu gewährleisten.

---

## 1. System-Struktur

Der **Main Controller** (`main.py`) agiert als zentraler Koordinator zwischen den spezialisierten Layern:

* **Hardware Layer**: Zentralisierte Instanziierung der Treiber (I2C, UART).
* **Service Layer**: Abwicklung asynchroner Aufgaben wie NTP-Sync und WLAN-Management.
* **UI Layer**: Logikfreie Darstellung der Daten auf dem LCD 2004.

## 2. Dateistruktur

| Datei | Funktion |
| :--- | :--- |
| `main.py` | Einstiegspunkt; enthält die `ShackClock`-Klasse und den Main-Loop. |
| `hardware_manager.py` | Dependency-Injection Container für alle Hardware-Referenzen. |
| `time_synchronizer.py` | Entscheidungslogik der Zeitquellen-Kaskade (Priorisierung). |
| `display_manager.py` | LCD-Steuerung, Custom-Characters und Layout-Definition. |
| `qth_locator.py` | Algorithmus zur Konvertierung von GPS-Koordinaten in den QTH-Locator. |
| `time_utils.py` | Funktionen für MEZ/MESZ-Umrechnung und Zeitstempel-Korrektur. |
| `config.json` | Konfigurationsparameter für WLAN, NTP und Hardware-Optionen. |

## 3. Synchronisations-Strategie

Der `TimeSynchronizer` nutzt eine Prioritäten-Kaskade, um eine Stratum-0-nahe Präzision zu erreichen:

1.  **GPS (Priorität 1)**: Primärquelle bei gültigem Fix. Die Firmware kompensiert die Latenz zwischen NMEA-Empfang und Systemzeit-Update.
2.  **NTP (Priorität 2)**: Fallback bei fehlendem GPS-Fix und aktiver WLAN-Verbindung.
3.  **RTC (Priorität 3)**: Permanentes lokales Fundament durch das DS3231-Modul. Die RTC wird bei jedem erfolgreichen GPS/NTP-Sync abgeglichen, um Drift zu minimieren.

## 4. QTH-Locator Berechnung

Die Berechnung des 6-stelligen Locators erfolgt in der `qth_locator.py` basierend auf der aktuellen GPS-Position. Die Logik überführt Längen- und Breitengrade in Felder, Quadrate und Sub-Quadrate.

Die mathematische Basis für die Feld-Ermittlung (erste zwei Zeichen):

$$Feld_{Long} = \text{chr}\left(65 + \text{int}\left(\frac{Long + 180}{20}\right)\right)$$
$$Feld_{Lat} = \text{chr}\left(65 + \text{int}\left(\frac{Lat + 90}{10}\right)\right)$$

## 5. Performance & Echtzeit-Handling

Da MicroPython auf dem RP2040 Single-Core-zentriert arbeitet, wird ein striktes Polling-Verfahren genutzt:

* **GPS-Polling**: Der UART-Buffer wird alle 10ms geleert, um Datenverlust bei den NMEA-Sätzen zu verhindern.
* **Asynchrone Wartung**: WLAN-Reconnects und NTP-Abfragen blockieren nicht den Sekundenwechsel des Displays.
* **Stabilisierung**: Ein modifizierter LCD-Treiber unterdrückt fehlerhafte Zeichenbildungen bei Soft-Resets.

## 6. Diagnose (Debug-Modus)

Der über die `config.json` aktivierbare Debug-Modus (`"debug_mode": "GPS"`) dient der Feld-Analyse:

* Echtzeit-Anzeige der Roh-NMEA-Paketzähler.
* Visualisierung von Satellitenanzahl und Fix-Qualität (3D/2D).
* Direkter Abgleich der GPS-Koordinaten mit dem berechneten Locator.