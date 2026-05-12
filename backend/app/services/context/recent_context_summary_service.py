from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean
from typing import Any, Sequence


@dataclass(frozen=True)
class ContextDailyEntry:
    """
    Neutral daily context DTO for LLM summarization.

    This model should be filled from diary/check-in history.
    It must not depend on PatternAnalysisService or scoring models.
    """

    entry_date: date
    emotion_marker: str | None = None
    diary_note: str | None = None

    sleep_duration_hours: float | None = None
    sleep_quality: str | None = None
    sleep_regularity: str | None = None

    physical_activity_minutes: float | None = None
    sedentary_time_minutes: float | None = None
    outdoor_time_minutes: float | None = None

    social_connectedness_score: float | None = None
    routine_regularity: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextMemory:
    """
    Neutral retrieved memory DTO.

    This should be produced by the real memory retrieval layer:
    pgvector / embedding retriever / fallback retriever.

    Do not pass raw embeddings here.
    Only pass text that can be safely inserted into an LLM prompt.
    """

    source: str
    text: str
    entry_date: date | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RecentContextSummaryService:
    """
    Builds compact, non-diagnostic Russian context for the LLM.

    This service does not:
    - calculate wellbeing scores
    - assign clinical labels
    - diagnose
    - use weighted severity logic
    - decide final support mode

    It only prepares a short user-context summary for prompt injection.
    """

    DEFAULT_DAYS = 14

    def build_summary(
        self,
        *,
        entries: Sequence[ContextDailyEntry],
        retrieved_memories: Sequence[ContextMemory],
        latest_user_message: str | None,
        latest_diary_note: str | None,
        max_chars: int = 1600,
    ) -> str:
        if not entries and not retrieved_memories and not latest_user_message and not latest_diary_note:
            return (
                "История пользователя пока недоступна. "
                "Отвечай на основе текущего сообщения, мягко и без предположений."
            )

        lines: list[str] = []

        if entries:
            lines.extend(self._build_recent_history_lines(entries))
        else:
            lines.append(
                "История за последние дни ограничена или недоступна. "
                "Не делай уверенных выводов о долгосрочных паттернах."
            )

        current_lines = self._build_current_context_lines(
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
        )
        if current_lines:
            lines.append("")
            lines.extend(current_lines)

        memory_lines = self._format_memories(retrieved_memories[:5])
        if memory_lines:
            lines.append("")
            lines.append("Релевантные прошлые записи:")
            lines.extend(memory_lines)

        lines.append("")
        lines.append(
            "Инструкция для ответа: используй этот контекст только для мягкой персонализации. "
            "Не упоминай внутренний анализ, оценки, баллы или диагнозы. "
            "Формулируй осторожно: «похоже», «в последних записях встречается», "
            "«может быть связано». Не перегружай пользователя советами."
        )

        summary = "\n".join(line for line in lines if line is not None).strip()
        return self._truncate(summary, max_chars=max_chars)

    def _build_recent_history_lines(self, entries: Sequence[ContextDailyEntry]) -> list[str]:
        sorted_entries = sorted(entries, key=lambda item: item.entry_date)
        tail = sorted_entries[-self.DEFAULT_DAYS :]

        lines: list[str] = []
        lines.append(
            f"Период контекста: {tail[0].entry_date.isoformat()} .. "
            f"{tail[-1].entry_date.isoformat()} ({len(tail)} записей)."
        )

        emotion_line = self._build_emotion_line(tail)
        if emotion_line:
            lines.append(emotion_line)

        sleep_line = self._build_sleep_line(tail)
        if sleep_line:
            lines.append(sleep_line)

        activity_line = self._build_activity_line(tail)
        if activity_line:
            lines.append(activity_line)

        social_line = self._build_social_line(tail)
        if social_line:
            lines.append(social_line)

        routine_line = self._build_routine_line(tail)
        if routine_line:
            lines.append(routine_line)

        theme_lines = self._build_repeated_theme_lines(tail)
        if theme_lines:
            lines.extend(theme_lines)

        recent_change_line = self._build_recent_change_line(tail)
        if recent_change_line:
            lines.append(recent_change_line)

        return lines

    def _build_current_context_lines(
        self,
        *,
        latest_user_message: str | None,
        latest_diary_note: str | None,
    ) -> list[str]:
        lines: list[str] = []

        if latest_diary_note:
            lines.append(f"Актуальная дневниковая заметка: {self._fmt_text(latest_diary_note, max_len=320)}")

        if latest_user_message:
            lines.append(f"Текущее сообщение пользователя: {self._fmt_text(latest_user_message, max_len=320)}")

        return lines

    def _build_emotion_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        emotions = [self._fmt_text(item.emotion_marker, max_len=40) for item in entries if item.emotion_marker]
        emotions = [emotion for emotion in emotions if emotion]

        if not emotions:
            return None

        recent = ", ".join(emotions[-5:])
        dominant = self._most_common(emotions, limit=3)

        if dominant:
            return (
                f"Эмоции в последних записях: {recent}. "
                f"Чаще встречались: {', '.join(dominant)}."
            )

        return f"Эмоции в последних записях: {recent}."

    def _build_sleep_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        sleep_values = [
            item.sleep_duration_hours
            for item in entries
            if item.sleep_duration_hours is not None and item.sleep_duration_hours >= 0
        ]

        sleep_quality_values = [
            self._fmt_text(item.sleep_quality, max_len=40)
            for item in entries
            if item.sleep_quality
        ]
        sleep_quality_values = [value for value in sleep_quality_values if value]

        sleep_regularity_values = [
            self._fmt_text(item.sleep_regularity, max_len=40)
            for item in entries
            if item.sleep_regularity
        ]
        sleep_regularity_values = [value for value in sleep_regularity_values if value]

        parts: list[str] = []

        if sleep_values:
            avg_sleep = mean(sleep_values)
            parts.append(f"средняя длительность сна около {avg_sleep:.1f} ч")

            short_sleep_days = sum(1 for value in sleep_values if value < 6)
            very_short_sleep_days = sum(1 for value in sleep_values if value < 4)

            if very_short_sleep_days:
                parts.append(
                    f"в {very_short_sleep_days} дн. сон был очень коротким"
                )
            elif short_sleep_days:
                parts.append(
                    f"в {short_sleep_days} дн. сон был короче обычного"
                )

        if sleep_quality_values:
            dominant_quality = self._most_common(sleep_quality_values, limit=2)
            if dominant_quality:
                parts.append(f"качество сна часто отмечалось как: {', '.join(dominant_quality)}")

        if sleep_regularity_values:
            dominant_regularity = self._most_common(sleep_regularity_values, limit=2)
            if dominant_regularity:
                parts.append(f"регулярность сна часто отмечалась как: {', '.join(dominant_regularity)}")

        if not parts:
            return None

        return "Сон: " + "; ".join(parts) + "."

    def _build_activity_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        activity_values = [
            item.physical_activity_minutes
            for item in entries
            if item.physical_activity_minutes is not None and item.physical_activity_minutes >= 0
        ]

        outdoor_values = [
            item.outdoor_time_minutes
            for item in entries
            if item.outdoor_time_minutes is not None and item.outdoor_time_minutes >= 0
        ]

        sedentary_values = [
            item.sedentary_time_minutes
            for item in entries
            if item.sedentary_time_minutes is not None and item.sedentary_time_minutes >= 0
        ]

        parts: list[str] = []

        if activity_values:
            avg_activity = mean(activity_values)
            parts.append(f"средняя активность около {avg_activity:.0f} мин/день")

            low_activity_days = sum(1 for value in activity_values if value < 15)
            if low_activity_days >= 2:
                parts.append(f"в {low_activity_days} дн. активность была низкой")

        if outdoor_values:
            avg_outdoor = mean(outdoor_values)
            parts.append(f"время на улице около {avg_outdoor:.0f} мин/день")

            low_outdoor_days = sum(1 for value in outdoor_values if value < 15)
            if low_outdoor_days >= 2:
                parts.append(f"в {low_outdoor_days} дн. было мало времени на улице")

        if sedentary_values:
            avg_sedentary = mean(sedentary_values)
            if avg_sedentary >= 480:
                parts.append("в записях заметно много сидячего времени")

        if not parts:
            return None

        return "Активность и восстановление: " + "; ".join(parts) + "."

    def _build_social_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        social_values = [
            item.social_connectedness_score
            for item in entries
            if item.social_connectedness_score is not None
        ]

        if not social_values:
            return None

        avg_social = mean(social_values)
        low_social_days = sum(1 for value in social_values if value <= 2)

        if low_social_days >= 2:
            return (
                f"Социальная связь: среднее около {avg_social:.1f}/5; "
                f"в {low_social_days} дн. отмечалась низкая включенность или мало контакта."
            )

        return f"Социальная связь: среднее около {avg_social:.1f}/5."

    def _build_routine_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        routine_values = [
            self._fmt_text(item.routine_regularity, max_len=40)
            for item in entries
            if item.routine_regularity
        ]
        routine_values = [value for value in routine_values if value]

        if not routine_values:
            return None

        dominant = self._most_common(routine_values, limit=2)
        if not dominant:
            return None

        return f"Рутина: в последних записях часто встречалось: {', '.join(dominant)}."

    def _build_repeated_theme_lines(self, entries: Sequence[ContextDailyEntry]) -> list[str]:
        notes = [
            self._fmt_text(item.diary_note, max_len=500).lower()
            for item in entries
            if item.diary_note
        ]
        notes = [note for note in notes if note]

        if not notes:
            return []

        theme_keywords: dict[str, tuple[str, ...]] = {
            "усталость или истощение": (
                "устал",
                "устала",
                "нет сил",
                "истощ",
                "выгор",
                "разбит",
                "разбита",
            ),
            "учебная или рабочая нагрузка": (
                "учеб",
                "работ",
                "дедлайн",
                "экзамен",
                "проект",
                "задач",
            ),
            "изоляция или одиночество": (
                "одинок",
                "не с кем",
                "не хочу общаться",
                "изол",
                "закрыться",
                "никому",
            ),
            "тревожные мысли или накручивание": (
                "тревог",
                "накруч",
                "мысли",
                "пережива",
                "страшно",
                "паник",
            ),
            "конфликт или напряжение в отношениях": (
                "ссор",
                "конфликт",
                "поруг",
                "отношен",
                "обид",
            ),
        }

        detected: list[str] = []

        for theme_name, keywords in theme_keywords.items():
            count = 0
            for note in notes:
                if any(keyword in note for keyword in keywords):
                    count += 1

            if count >= 2:
                detected.append(f"{theme_name} ({count} запис.)")

        if not detected:
            return []

        return [
            "Повторяющиеся темы в дневниковых заметках: "
            + "; ".join(detected)
            + "."
        ]

    def _build_recent_change_line(self, entries: Sequence[ContextDailyEntry]) -> str | None:
        if len(entries) < 6:
            return None

        first_part = entries[:-3]
        last_part = entries[-3:]

        first_negative = self._negative_signal_count(first_part)
        last_negative = self._negative_signal_count(last_part)

        if last_negative >= first_negative + 2:
            return (
                "Недавнее изменение: последние несколько записей выглядят более тяжелыми, "
                "чем более ранняя часть периода. Формулируй это осторожно, без категоричных выводов."
            )

        return None

    def _negative_signal_count(self, entries: Sequence[ContextDailyEntry]) -> int:
        negative_emotion_markers = (
            "груст",
            "трев",
            "зл",
            "устал",
            "плохо",
            "одинок",
            "раздраж",
            "стресс",
        )

        count = 0

        for entry in entries:
            emotion = (entry.emotion_marker or "").lower()
            note = (entry.diary_note or "").lower()

            if emotion and any(marker in emotion for marker in negative_emotion_markers):
                count += 1

            if note and any(marker in note for marker in negative_emotion_markers):
                count += 1

            if entry.sleep_duration_hours is not None and entry.sleep_duration_hours < 6:
                count += 1

            if entry.social_connectedness_score is not None and entry.social_connectedness_score <= 2:
                count += 1

            if entry.physical_activity_minutes is not None and entry.physical_activity_minutes < 15:
                count += 1

        return count

    def _format_memories(self, memories: Sequence[ContextMemory]) -> list[str]:
        out: list[str] = []

        for memory in memories:
            if not memory.text or not memory.text.strip():
                continue

            iso_date = memory.entry_date.isoformat() if memory.entry_date else "дата неизвестна"
            source = self._fmt_text(memory.source, max_len=40) or "источник неизвестен"
            text = self._fmt_text(memory.text, max_len=220)

            out.append(f"- [{iso_date}] ({source}) {text}")

        return out

    def _most_common(self, values: Sequence[str], *, limit: int) -> list[str]:
        counts: dict[str, int] = {}

        for value in values:
            clean = self._fmt_text(value, max_len=60).lower()
            if not clean:
                continue
            counts[clean] = counts.get(clean, 0) + 1

        sorted_items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [item[0] for item in sorted_items[:limit]]

    def _fmt_text(self, value: str | None, max_len: int = 120) -> str:
        if not value:
            return ""

        clean = " ".join(value.strip().split())

        if len(clean) <= max_len:
            return clean

        return clean[:max_len].rstrip() + "..."

    def _truncate(self, value: str, *, max_chars: int) -> str:
        if len(value) <= max_chars:
            return value

        truncated = value[:max_chars].rstrip()

        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.75:
            truncated = truncated[:last_newline].rstrip()

        return truncated + "\n...контекст сокращен из-за лимита длины."