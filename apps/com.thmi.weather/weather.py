import json
import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)
WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy", 45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Showers", 81: "Showers", 82: "Heavy showers",
       95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"}


class Weather(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.weather")
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "Weather", lv.SYMBOL.SETTINGS, self._settings)
        self.city_l = thmi_ui.text(sc, "", 6, 40, lv.font_montserrat_14, None, 228)
        self.temp = thmi_ui.text(sc, "", 6, 64, lv.font_montserrat_24, None, 228)
        self.now = thmi_ui.text(sc, "", 6, 100, lv.font_montserrat_20, None, 228)
        self.more = thmi_ui.text(sc, "", 6, 136, lv.font_montserrat_14, None, 228)
        self.days = thmi_ui.text(sc, "", 6, 176, lv.font_montserrat_14, None, 228)
        self.setContentView(sc)

    def _settings(self, e):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [{"title": "City", "key": "city", "ui": "textarea", "placeholder": "London", "default_value": ""},
                                     {"title": "Units", "key": "units", "ui": "radiobuttons", "default_value": "c",
                                      "ui_options": [("Celsius, km/h", "c"), ("Fahrenheit, mph", "f")]}])
        self.startActivity(intent)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._load())

    async def _load(self):
        city = self.prefs.get_string("city", "").strip()
        if not city:
            self.temp.set_text("Tap the gear\nand type your city")
            return
        f = self.prefs.get_string("units", "c") == "f"
        try:
            self.temp.set_text("Loading...")
            g = json.loads(await thmi_net.get_url("https://geocoding-api.open-meteo.com/v1/search?name=%s&count=1" % thmi_net.quote(city)))
            r = g["results"][0]
            u = "&temperature_unit=fahrenheit&wind_speed_unit=mph" if f else ""
            w = json.loads(await thmi_net.get_url(
                "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,wind_speed_10m,weather_code,relative_humidity_2m"
                "&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto&forecast_days=4%s" % (r["latitude"], r["longitude"], u)))
        except Exception as e:
            logger.warning("weather: %s", e)
            self.temp.set_text("Can't load the weather.\nCheck the city and Wi-Fi.")
            return
        c, d = w["current"], w["daily"]
        deg = "F" if f else "C"
        self.city_l.set_text("%s, %s" % (r["name"], r.get("country", "")))
        self.temp.set_text("%d %s" % (round(c["temperature_2m"]), deg))
        self.now.set_text(WMO.get(c["weather_code"], "Weather"))
        self.more.set_text("Wind %d %s    Humidity %d%%" % (round(c["wind_speed_10m"]), "mph" if f else "km/h", c["relative_humidity_2m"]))
        lines = []
        for i in range(1, 4):
            lines.append("%s   %d / %d %s   %s" % (d["time"][i][5:], round(d["temperature_2m_max"][i]), round(d["temperature_2m_min"][i]), deg, WMO.get(d["weather_code"][i], "")))
        self.days.set_text("\n\n".join(lines))
