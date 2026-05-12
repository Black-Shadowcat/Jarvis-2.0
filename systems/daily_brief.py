import json
import os
import random
import shutil
from datetime import datetime, date
from typing import Optional

DATA_PATH    = os.path.join(os.path.dirname(__file__), "..", "data", "daily_brief_memory.json")
ARCHIVE_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "daily_brief_archive")

_EMPTY_STATE = {
    "date": "",
    "last_morning_brief": None,
    "pause_tracking": {
        "last_activity": None,
        "pause_threshold_minutes": 30,
        "long_absence_threshold_minutes": 90,
    },
    "status_checks": [],
    "evening_briefing": {
        "done": False,
        "scheduled_after": "17:00",
    },
}


class DailyBrief:
    def __init__(self):
        self._data: dict = self.load()
        self._loc: dict = {}

    def set_locale(self, loc: dict) -> None:
        self._loc = loc

    def _t(self, *keys, default=""):
        """Navigate nested locale keys and return the value."""
        v = self._loc
        for k in keys:
            if not isinstance(v, dict):
                return default
            v = v.get(k, default)
        return v

    # ── Persistence ──────────────────────────────────────────────────────────

    def load(self) -> dict:
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != str(date.today()):
                data = self._fresh_state(preserve_from=data)
                self._save(data)
        except (FileNotFoundError, json.JSONDecodeError):
            data = self._fresh_state()
            self._save(data)
        self._data = data
        return data

    def _save(self, data: dict) -> None:
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self) -> None:
        self._save(self._data)

    def _fresh_state(self, preserve_from: dict = None) -> dict:
        state = json.loads(json.dumps(_EMPTY_STATE))
        state["date"] = str(date.today())
        if preserve_from:
            pt = preserve_from.get("pause_tracking", {})
            for key in ("pause_threshold_minutes", "long_absence_threshold_minutes"):
                if key in pt:
                    state["pause_tracking"][key] = pt[key]
        return state

    # ── Archive & Reset ───────────────────────────────────────────────────────

    def archive(self) -> None:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        dest = os.path.join(ARCHIVE_DIR, f"{self._data.get('date', 'unknown')}.json")
        shutil.copy2(DATA_PATH, dest)

    def reset(self) -> None:
        self.archive()
        self._data = self._fresh_state(preserve_from=self._data)
        self.save()

    # ── Activity Tracking ─────────────────────────────────────────────────────

    def update_activity(self) -> None:
        self._data["pause_tracking"]["last_activity"] = datetime.now().isoformat()
        self.save()

    def _minutes_since_last_activity(self) -> Optional[float]:
        ts = self._data["pause_tracking"].get("last_activity")
        if not ts:
            return None
        delta = datetime.now() - datetime.fromisoformat(ts)
        return delta.total_seconds() / 60

    # ── Trigger Detection ─────────────────────────────────────────────────────

    def detect_morning_trigger(self) -> bool:
        brief = self._data.get("last_morning_brief")
        if brief:
            return False
        return datetime.now().hour >= 6

    def detect_pause_return(self) -> bool:
        minutes = self._minutes_since_last_activity()
        if minutes is None:
            return False
        threshold = self._data["pause_tracking"]["pause_threshold_minutes"]
        long_threshold = self._data["pause_tracking"]["long_absence_threshold_minutes"]
        return threshold <= minutes < long_threshold

    def detect_long_absence(self) -> bool:
        minutes = self._minutes_since_last_activity()
        if minutes is None:
            return False
        threshold = self._data["pause_tracking"]["long_absence_threshold_minutes"]
        return minutes >= threshold

    def detect_evening_trigger(self) -> bool:
        if self._data["evening_briefing"]["done"]:
            return False
        scheduled = self._data["evening_briefing"]["scheduled_after"]
        hour, minute = map(int, scheduled.split(":"))
        now = datetime.now()
        return now.hour > hour or (now.hour == hour and now.minute >= minute)

    # ── Mail ID Tracking ──────────────────────────────────────────────────────

    def compare_mail_ids(self, previous_ids: list, current_ids: list) -> dict:
        prev = set(previous_ids)
        curr = set(current_ids)
        return {
            "new_ids":     list(curr - prev),
            "deleted_ids": list(prev - curr),
            "unchanged_ids": list(prev & curr),
            "new_count":   len(curr - prev),
            "deleted_count": len(prev - curr),
            "current_count": len(curr),
        }

    def get_known_mail_ids(self) -> list:
        brief = self._data.get("last_morning_brief")
        if not brief:
            return []
        return brief.get("mail_ids_mentioned", [])

    # ── Briefing Generators ───────────────────────────────────────────────────

    def record_morning_brief(self, mails: list, tasks: list, reminders: list,
                              notes: list, weather: str = "") -> None:
        """Record morning brief state without generating text (LLM handles the greeting)."""
        mail_ids = [f"{m.get('sender','')}_{m.get('subject','')}" for m in mails]
        self._data["last_morning_brief"] = {
            "timestamp": datetime.now().isoformat(),
            "trigger": "first_activation",
            "mail_ids_mentioned": mail_ids,
            "mail_count_mentioned": len(mails),
            "task_count_mentioned": len(tasks),
            "reminder_count_mentioned": len(reminders),
            "note_pending_mentioned": len(notes) > 0,
            "weather_mentioned": weather,
        }
        self.update_activity()

    def generate_morning_brief(self, weather: str, mails: list, tasks: list,
                                reminders: list, notes: list, user_address: str) -> str:
        mail_ids = [f"{m.get('sender','')}_{m.get('subject','')}" for m in mails]

        self._data["last_morning_brief"] = {
            "timestamp": datetime.now().isoformat(),
            "trigger": "first_activation",
            "mail_ids_mentioned": mail_ids,
            "mail_count_mentioned": len(mails),
            "task_count_mentioned": len(tasks),
            "reminder_count_mentioned": len(reminders),
            "note_pending_mentioned": len(notes) > 0,
            "weather_mentioned": weather,
        }
        self.update_activity()

        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        mb = self._t("morning_brief") or {}
        day_names = self._t("day_names") or ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
        g = self._t("greetings") or {}

        if hour < 11:
            greeting = g.get("morning", "Guten Morgen")
        elif hour < 14:
            greeting = g.get("midday", "Guten Tag")
        elif hour < 18:
            greeting = g.get("afternoon", "Guten Nachmittag")
        else:
            greeting = g.get("evening", "Guten Abend")

        parts = [f"{greeting}, {user_address}."]

        # Day context (morning only)
        if hour < 13:
            day = day_names[weekday]
            tpl = mb.get("weekend_day", "Genießen Sie Ihren {day}.") if weekday >= 5 else mb.get("weekday", "Es ist {day}.")
            parts.append(tpl.format(day=day))

        # Weather + advisory
        if weather:
            parts.append(weather.rstrip(".") + ".")
            wloc = self._t("weather") or {}
            w = weather.lower()
            if any(x in w for x in wloc.get("rain_keywords", ["regen","schauer"])):
                parts.append(wloc.get("rain", "Vergessen Sie Ihren Schirm nicht."))
            elif any(x in w for x in wloc.get("snow_keywords", ["schnee","eis"])):
                parts.append(wloc.get("snow", "Die Straßen könnten glatt sein."))
            elif any(x in w for x in wloc.get("storm_keywords", ["sturm","gewitter"])):
                parts.append(wloc.get("storm", "Starker Wind heute."))
            elif any(x in w for x in wloc.get("sunny_keywords", ["sonnig","klar"])):
                parts.append(wloc.get("sunny", "Ein schöner Tag draußen."))

        # Mail
        if mails:
            n = len(mails)
            if n == 1:
                parts.append(mb.get("mail_1", "Eine neue Mail wartet auf Sie."))
            elif n <= 4:
                parts.append(mb.get("mail_few", "{n} ungelesene Mails.").format(n=n))
            else:
                parts.append(mb.get("mail_many", "{n} ungelesene Mails in Ihrem Postfach.").format(n=n))

        # Tasks and reminders
        if tasks and reminders:
            t, r = len(tasks), len(reminders)
            tw = mb.get("task_word_1","Aufgabe") if t==1 else mb.get("task_word_many","Aufgaben")
            rw = mb.get("reminder_word_1","Erinnerung") if r==1 else mb.get("reminder_word_many","Erinnerungen")
            parts.append(mb.get("tasks_and_reminders","{t} {task_word} und {r} {reminder_word} stehen noch aus.").format(t=t,task_word=tw,r=r,reminder_word=rw))
        elif tasks:
            t = len(tasks)
            tw = mb.get("task_word_1","Aufgabe") if t==1 else mb.get("task_word_many","Aufgaben")
            parts.append(mb.get("only_tasks","{t} {task_word} auf der Liste.").format(t=t,task_word=tw))
        elif reminders:
            r = len(reminders)
            rw = mb.get("reminder_word_1","Erinnerung") if r==1 else mb.get("reminder_word_many","Erinnerungen")
            parts.append(mb.get("only_reminders","{r} {reminder_word} für heute.").format(r=r,reminder_word=rw))

        # Notes
        if notes:
            n = len(notes)
            nw = mb.get("note_word_1","Notiz") if n==1 else mb.get("note_word_many","Notizen")
            parts.append(mb.get("notes","{n} offene {note_word} in Obsidian.").format(n=n,note_word=nw))

        # Closing
        if not mails and not tasks and not reminders and not notes:
            parts.append(random.choice(mb.get("no_items",["Alles erledigt — ein ruhiger Start."])))
        else:
            parts.append(random.choice(mb.get("closing",["Ich stehe bereit."])))

        return " ".join(parts)

    def generate_pause_brief(self, current_mails: list, user_address: str) -> str:
        known_ids = self.get_known_mail_ids()
        current_ids = [f"{m.get('sender','')}_{m.get('subject','')}" for m in current_mails]
        diff = self.compare_mail_ids(known_ids, current_ids)

        self._data["status_checks"].append({
            "timestamp": datetime.now().isoformat(),
            "trigger": "pause_return",
            "new_count": diff["new_count"],
            "deleted_count": diff["deleted_count"],
            "current_count": diff["current_count"],
        })
        # Baseline aktualisieren — nächster Vergleich gegen aktuellen Stand, nicht Morgen
        if self._data.get("last_morning_brief"):
            self._data["last_morning_brief"]["mail_ids_mentioned"] = current_ids
            self._data["last_morning_brief"]["mail_count_mentioned"] = len(current_ids)
        self.update_activity()

        pb = self._t("pause_brief") or {}
        if diff["new_count"] > 0:
            n = diff["new_count"]
            new_ids_set = set(diff["new_ids"])
            new_mails = [m for m in current_mails
                         if f"{m.get('sender','')}_{m.get('subject','')}" in new_ids_set]
            senders = [m.get("sender", "").split("<")[0].strip() or m.get("sender", "Unbekannt")
                       for m in new_mails]
            if n == 1:
                return random.choice([t.format(address=user_address, sender=senders[0])
                                      for t in pb.get("new_mail_1", [f"Willkommen zurück, {user_address}. Eine neue Mail von {senders[0]}."])])
            elif n == 2:
                return pb.get("new_mail_2", "Willkommen zurück, {address}. {n} neue Mails — von {s1} und {s2}.").format(
                    address=user_address, n=n, s1=senders[0], s2=senders[1])
            else:
                return pb.get("new_mail_many", "Willkommen zurück, {address}. {n} neue Mails — unter anderem von {sender}.").format(
                    address=user_address, n=n, sender=senders[0])
        return random.choice([t.format(address=user_address)
                               for t in pb.get("no_mail", [f"Willkommen zurück, {user_address}."])])

    def generate_absence_brief(self, current_mails: list, user_address: str) -> str:
        known_ids = self.get_known_mail_ids()
        current_ids = [f"{m.get('sender','')}_{m.get('subject','')}" for m in current_mails]
        diff = self.compare_mail_ids(known_ids, current_ids)

        self._data["status_checks"].append({
            "timestamp": datetime.now().isoformat(),
            "trigger": "long_absence_return",
            "new_count": diff["new_count"],
            "deleted_count": diff["deleted_count"],
            "current_count": diff["current_count"],
        })
        if self._data.get("last_morning_brief"):
            self._data["last_morning_brief"]["mail_ids_mentioned"] = current_ids
            self._data["last_morning_brief"]["mail_count_mentioned"] = len(current_ids)
        self.update_activity()

        ab = self._t("absence_brief") or {}
        if diff["new_count"] > 0:
            n = diff["new_count"]
            new_ids_set = set(diff["new_ids"])
            new_mails = [m for m in current_mails
                         if f"{m.get('sender','')}_{m.get('subject','')}" in new_ids_set]
            senders = [m.get("sender", "").split("<")[0].strip() or m.get("sender", "Unbekannt")
                       for m in new_mails]
            if n == 1:
                return random.choice([t.format(address=user_address, sender=senders[0])
                                      for t in ab.get("new_mail_1", [f"Schön, Sie wieder zu haben, {user_address}. Eine neue Mail von {senders[0]}."])])
            elif n == 2:
                return ab.get("new_mail_2", "Schön, Sie wieder zu haben, {address}. {n} neue Mails — von {s1} und {s2}.").format(
                    address=user_address, n=n, s1=senders[0], s2=senders[1])
            else:
                return ab.get("new_mail_many", "Willkommen zurück, {address}. {n} neue Mails in Ihrer Abwesenheit — unter anderem von {sender}.").format(
                    address=user_address, n=n, sender=senders[0])
        return random.choice([t.format(address=user_address)
                               for t in ab.get("no_mail", [f"Schön, Sie wieder zu haben, {user_address}. Das Postfach war ruhig."])])

    def generate_evening_brief(self, mails: list, weather: str, user_address: str) -> str:
        self._data["evening_briefing"]["done"] = True
        self.update_activity()

        eb = self._t("evening_brief") or {}
        parts = [eb.get("opening", "Feierabend, {address}.").format(address=user_address)]
        if mails:
            n = len(mails)
            mw = eb.get("mail_word_1","Mail") if n==1 else eb.get("mail_word_many","Mails")
            parts.append(eb.get("mail","Im Postfach: {n} ungelesene {mail_word}.").format(n=n,mail_word=mw))
        else:
            parts.append(eb.get("no_mail","Postfach ist leer."))
        if weather:
            parts.append(weather)
        return " ".join(parts)

    # ── State Accessors ───────────────────────────────────────────────────────

    def mark_evening_done(self) -> None:
        self._data["evening_briefing"]["done"] = True
        self.save()

    def get_state(self) -> dict:
        return self._data
