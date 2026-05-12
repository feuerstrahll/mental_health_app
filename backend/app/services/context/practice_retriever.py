from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Sequence


class PracticeCategory(StrEnum):
    BREATHING = "дыхательные_упражнения"
    GROUNDING = "заземление"
    SLEEP = "гигиена_сна"
    BEHAVIOURAL_ACTIVATION = "поведенческая_активация"
    BRIEF_CBT = "краткие_когнитивные_техники"
    MINDFULNESS = "осознанность"
    JOURNALING = "дневниковые_практики"
    SOCIAL_CONNECTION = "социальная_связь"
    CRISIS = "кризисная_поддержка"


class EvidenceTier(StrEnum):
    STRONGER_EVIDENCE = "более_сильная_доказательная_база"
    USEFUL_NEXT = "полезно_как_дополнение"
    CONSERVATIVE = "использовать_осторожно"
    CRISIS_PROTOCOL = "кризисный_протокол"


@dataclass(frozen=True)
class PracticeCard:
    card_id: str
    category: PracticeCategory
    title: str
    when_to_use: str
    description: str
    steps: list[str]
    contraindications: list[str]
    safety_note: str
    chatbot_safety_note: str
    source_short_citations: list[str]
    tags: tuple[str, ...]
    evidence_tier: EvidenceTier
    retrieval_keywords: tuple[str, ...] = field(default_factory=tuple)

    def as_compact_text(self) -> str:
        steps = "; ".join(self.steps[:5])
        contraindications = "; ".join(self.contraindications[:3])
        citations = ", ".join(self.source_short_citations[:3])

        return (
            f"id={self.card_id}; "
            f"категория={self.category.value}; "
            f"название={self.title}; "
            f"когда_использовать={self.when_to_use}; "
            f"описание={self.description}; "
            f"шаги={steps}; "
            f"ограничения={contraindications}; "
            f"заметка_безопасности={self.chatbot_safety_note}; "
            f"источники={citations}"
        )


class PracticeRetriever:
    """
    Возвращает только заранее одобренные практики.

    Важно:
    - Не ищет материалы в интернете.
    - Не передает модели произвольный внешний текст.
    - Модель может ссылаться только на источники из карточек.
    - Кризисная поддержка — это не практика, а отдельный маршрут эскалации.
    """

    ADVICE_KEYWORDS = (
        "совет",
        "практика",
        "упражнение",
        "что делать",
        "как справиться",
        "как справится",
        "помоги",
        "подскажи",
        "как мне быть",
        "что можно сделать",
        "дай технику",
        "дай упражнение",
    )

    CRISIS_KEYWORDS = (
        "суицид",
        "самоубийство",
        "убить себя",
        "не хочу жить",
        "не могу жить",
        "не могу быть в безопасности",
        "не могу себя контролировать",
        "навредить себе",
        "причинить себе вред",
        "порезать себя",
        "передозировка",
        "выпить таблетки",
        "покончить с собой",
        "исчезнуть навсегда",
        "лучше бы меня не было",
    )

    CATEGORY_KEYWORDS: dict[PracticeCategory, tuple[str, ...]] = {
        PracticeCategory.BREATHING: (
            "дыхание",
            "дышать",
            "выдох",
            "вдох",
            "паника",
            "тревога",
            "стресс",
            "напряжение",
            "задыхаюсь",
            "не могу дышать",
        ),
        PracticeCategory.GROUNDING: (
            "заземление",
            "дереализация",
            "диссоциация",
            "здесь и сейчас",
            "мысли скачут",
            "не чувствую реальность",
            "все как будто нереально",
            "потерялся",
            "потерялась",
        ),
        PracticeCategory.SLEEP: (
            "сон",
            "уснуть",
            "бессонница",
            "не сплю",
            "не могу заснуть",
            "сбит режим",
            "плохо сплю",
            "просыпаюсь",
            "не высыпаюсь",
        ),
        PracticeCategory.BEHAVIOURAL_ACTIVATION: (
            "нет сил",
            "ничего не делаю",
            "избегаю",
            "прокрастинация",
            "мало ресурса",
            "устал",
            "устала",
            "выгорел",
            "выгорела",
            "нет мотивации",
            "не могу начать",
        ),
        PracticeCategory.BRIEF_CBT: (
            "накручиваю",
            "руминация",
            "мысли",
            "катастрофизирую",
            "переживаю",
            "слишком много думаю",
            "не могу остановить мысли",
            "думаю об одном и том же",
        ),
        PracticeCategory.MINDFULNESS: (
            "осознанность",
            "медитация",
            "расслабиться",
            "замедлиться",
            "быть в моменте",
            "собраться",
        ),
        PracticeCategory.JOURNALING: (
            "дневник",
            "записать",
            "письмо",
            "рефлексия",
            "запись",
            "заметка",
            "описать чувства",
        ),
        PracticeCategory.SOCIAL_CONNECTION: (
            "одиноко",
            "одиночество",
            "не с кем поговорить",
            "изолируюсь",
            "не хочу общаться",
            "нет поддержки",
            "никому не нужен",
            "никому не нужна",
            "хочу закрыться",
        ),
    }

    def __init__(self) -> None:
        self._cards = [
            PracticeCard(
                card_id="breathing_slow_exhale",
                category=PracticeCategory.BREATHING,
                title="Мягкое дыхание с длинным выдохом",
                when_to_use="когда есть стресс, тревога или напряжение, но нет признаков медицинской срочности",
                description=(
                    "Медленное дыхание с более длинным выдохом может помочь переключить внимание "
                    "из стрессовой спирали и мягко успокоить тело."
                ),
                steps=[
                    "Сядьте или встаньте с опорой.",
                    "Расслабьте плечи.",
                    "Вдохните через нос примерно на 4 счета.",
                    "Медленно выдохните примерно на 6 счетов.",
                    "Повторяйте 1–3 минуты, без усилия и без задержек дыхания.",
                ],
                contraindications=[
                    "Сильная одышка.",
                    "Боль или сдавление в груди.",
                    "Головокружение или ощущение, что можно упасть в обморок.",
                    "Фокус на дыхании усиливает панику.",
                    "Беременность или медицинские ограничения — не использовать задержки дыхания.",
                ],
                safety_note="Если становится хуже, кружится голова или усиливается паника — остановитесь и дышите обычно.",
                chatbot_safety_note=(
                    "Если от этого кружится голова, усиливается паника или становится трудно дышать — "
                    "остановитесь и дышите нормально. При боли в груди, сильной нехватке воздуха "
                    "или предобморочном состоянии нужна срочная медицинская помощь."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: сон и дыхательные практики",
                    "Финчем и соавт., 2023",
                ],
                tags=("дыхание", "стресс", "тревога", "паника", "сон", "безопасный_вариант"),
                evidence_tier=EvidenceTier.STRONGER_EVIDENCE,
                retrieval_keywords=("дыхание", "выдох", "паника", "тревога", "стресс", "напряжение"),
            ),
            PracticeCard(
                card_id="grounding_54321",
                category=PracticeCategory.GROUNDING,
                title="Заземление 5-4-3-2-1",
                when_to_use="когда тревожно, мысли скачут или хочется вернуться в момент здесь-и-сейчас",
                description=(
                    "Заземление помогает вернуть внимание к текущему моменту через внешние ощущения. "
                    "Это низкорисковая техника, но ее лучше предлагать с осторожной формулировкой."
                ),
                steps=[
                    "Назовите 5 вещей, которые видите.",
                    "Назовите 4 вещи, которых можете коснуться.",
                    "Назовите 3 звука, которые слышите.",
                    "Назовите 2 запаха.",
                    "Назовите 1 вкус или просто один предмет рядом.",
                ],
                contraindications=[
                    "Упражнение усиливает ощущение нереальности.",
                    "Появляются сильные травматические воспоминания.",
                    "Становится труднее ориентироваться.",
                ],
                safety_note="Если стало тревожнее, нереальнее или тяжелее — остановитесь и переключитесь на внешнюю опору.",
                chatbot_safety_note=(
                    "Если заземление делает состояние более нереальным, пугающим или дезориентирующим, "
                    "остановитесь и обратитесь к доверенному человеку или профессиональной поддержке."
                ),
                source_short_citations=[
                    "Клиника Кливленда: техники заземления",
                    "Чин и соавт., 2024",
                ],
                tags=("заземление", "тревога", "паника", "дереализация", "безопасный_режим"),
                evidence_tier=EvidenceTier.CONSERVATIVE,
                retrieval_keywords=("заземление", "паника", "тревога", "дереализация", "нереальность"),
            ),
            PracticeCard(
                card_id="sleep_winddown",
                category=PracticeCategory.SLEEP,
                title="Мягкая подготовка ко сну",
                when_to_use="если сбит режим сна, трудно уснуть или вечером мысли крутятся по кругу",
                description=(
                    "Сон чаще улучшается через регулярность, спокойное завершение дня, управление светом "
                    "и снижение стимуляции. При хронической бессоннице одних советов по сну может быть недостаточно."
                ),
                steps=[
                    "Выберите фиксированное время подъема на завтра.",
                    "За 30–60 минут до сна снизьте яркость света и экранов.",
                    "Сделайте короткий спокойный ритуал: вода, душ, тихая музыка или чтение.",
                    "Если мысль крутится в голове — запишите ее одной строкой.",
                    "Если не получается уснуть около 20 минут, встаньте и сделайте что-то спокойное, затем вернитесь, когда появится сонливость.",
                ],
                contraindications=[
                    "Почти полное отсутствие сна несколько дней.",
                    "Сильная дневная сонливость, влияющая на безопасность.",
                    "Громкий храп или остановки дыхания во сне.",
                    "Длительная бессонница, которая заметно нарушает жизнь.",
                ],
                safety_note="Если проблемы со сном долго продолжаются или влияют на безопасность, лучше обратиться за медицинской помощью.",
                chatbot_safety_note=(
                    "Если проблемы со сном продолжаются, мешают функционировать или вы почти не спите несколько дней, "
                    "лучше обратиться за медицинской помощью, а не полагаться только на самопомощь."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: рекомендации по сну",
                    "Клиника Мэйо: когнитивно-поведенческий подход при бессоннице",
                ],
                tags=("сон", "бессонница", "режим", "вечерний_ритуал"),
                evidence_tier=EvidenceTier.STRONGER_EVIDENCE,
                retrieval_keywords=("сон", "уснуть", "бессонница", "режим", "плохо сплю"),
            ),
            PracticeCard(
                card_id="behavioural_activation_tiny_step",
                category=PracticeCategory.BEHAVIOURAL_ACTIVATION,
                title="Один микрошаг на 5 минут",
                when_to_use="когда мало сил, есть избегание, перегруз или ощущение застревания",
                description=(
                    "Когда человеку плохо, избегание может временно снижать давление, но часто удерживает состояние на месте. "
                    "Микрошаг помогает мягко вернуть ощущение движения без давления на продуктивность."
                ),
                steps=[
                    "Выберите одну маленькую безопасную задачу или действие.",
                    "Уменьшите ее до версии на 5 минут.",
                    "Решите, где и когда начнете.",
                    "Сделайте только эти 5 минут, даже если мотивации мало.",
                    "После отметьте: стало чуть легче, так же или тяжелее?",
                ],
                contraindications=[
                    "Задача небезопасна.",
                    "Задача связана с травмой, насилием или серьезным внешним кризисом.",
                    "Пользователь не справляется с базовой заботой о себе.",
                ],
                safety_note="Цель — не продуктивность, а мягкая стабилизация.",
                chatbot_safety_note=(
                    "Если вы не можете справляться с базовой заботой о себе, почти не функционируете "
                    "или есть мысли навредить себе, лучше искать живую поддержку сейчас, "
                    "а не пытаться просто «собраться»."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: список маленьких дел",
                    "Кокрейновский обзор поведенческой активации, 2020",
                ],
                tags=("поведенческая_активация", "сниженное_настроение", "избегание", "перегруз", "истощение"),
                evidence_tier=EvidenceTier.STRONGER_EVIDENCE,
                retrieval_keywords=("нет сил", "избегаю", "прокрастинация", "выгорел", "выгорела", "мало ресурса"),
            ),
            PracticeCard(
                card_id="brief_cbt_reframe",
                category=PracticeCategory.BRIEF_CBT,
                title="Короткая проверка мысли",
                when_to_use="когда пользователь накручивает себя, тревожится или застрял в повторяющихся мыслях",
                description=(
                    "Короткая когнитивная техника помогает заметить мысль, проверить ее "
                    "и найти более сбалансированную формулировку."
                ),
                steps=[
                    "Поймайте одну конкретную мысль.",
                    "Спросите: это факт или предположение?",
                    "Назовите, что поддерживает эту мысль.",
                    "Назовите, что может говорить против нее.",
                    "Сформулируйте более мягкую и реалистичную версию.",
                    "Выберите один маленький следующий шаг.",
                ],
                contraindications=[
                    "Кризисное состояние или риск самоповреждения.",
                    "Острое травматическое переживание.",
                    "Ощущение потери связи с реальностью.",
                    "Сильная перегрузка — тогда использовать только один шаг.",
                ],
                safety_note="Это не спор с собой и не попытка обесценить чувства.",
                chatbot_safety_note=(
                    "Если мысли говорят навредить себе, вы не чувствуете себя в безопасности "
                    "или теряете связь с реальностью, остановите упражнение и обратитесь за срочной поддержкой."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: техники самопомощи",
                    "Кокрейновский обзор самопомощи на основе когнитивно-поведенческого подхода",
                ],
                tags=("мысли", "тревога", "руминация", "накручивание", "стресс"),
                evidence_tier=EvidenceTier.STRONGER_EVIDENCE,
                retrieval_keywords=("мысли", "накручиваю", "руминация", "катастрофизирую", "переживаю"),
            ),
            PracticeCard(
                card_id="mindfulness_1_minute",
                category=PracticeCategory.MINDFULNESS,
                title="Одна минута осознанного внимания",
                when_to_use="когда нужно мягко замедлиться, но без длинной медитации",
                description=(
                    "Осознанность — это мягкое внимание к настоящему моменту без оценки. "
                    "Практика должна быть необязательной, короткой и адаптируемой."
                ),
                steps=[
                    "Сядьте удобно, глаза можно оставить открытыми.",
                    "Назовите 3 вещи, которые видите, слышите или ощущаете.",
                    "На 3–5 дыханий просто заметите естественный ритм дыхания.",
                    "Когда мысли уходят — мягко возвращайтесь к комнате вокруг.",
                    "Завершите, почувствовав стопы, стул или опору тела.",
                ],
                contraindications=[
                    "Медитация усиливает панику.",
                    "Появляется ощущение оторванности от реальности.",
                    "Поднимаются травматические воспоминания.",
                ],
                safety_note="Если становится хуже, лучше перейти к внешнему заземлению или простой практической задаче.",
                chatbot_safety_note=(
                    "Если это усиливает панику, отстраненность или поток тяжелых воспоминаний, "
                    "остановитесь и переключитесь на что-то более конкретное: заземление с открытыми глазами, "
                    "ходьбу или контакт с близким."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: осознанность",
                    "Гоял и соавт., 2014",
                ],
                tags=("осознанность", "медитация", "стресс", "сон", "замедление"),
                evidence_tier=EvidenceTier.STRONGER_EVIDENCE,
                retrieval_keywords=("осознанность", "медитация", "расслабиться", "замедлиться"),
            ),
            PracticeCard(
                card_id="journaling_one_prompt",
                category=PracticeCategory.JOURNALING,
                title="Один бережный вопрос в дневник",
                when_to_use="когда пользователь хочет разобраться в чувствах или заметить паттерн дня",
                description=(
                    "Короткое структурированное письмо может помочь обработать чувства и выбрать следующий добрый шаг. "
                    "Не стоит превращать его в глубокое травматическое письмо внутри чатбота."
                ),
                steps=[
                    "Выберите один вопрос: «Что я чувствую прямо сейчас?»",
                    "Или: «Что произошло, что было важным, что мне нужно дальше?»",
                    "Пишите 5–10 минут.",
                    "Не пытайтесь сделать текст красивым.",
                    "Завершите одним добрым маленьким шагом для себя.",
                ],
                contraindications=[
                    "Письмо усиливает руминацию.",
                    "Пользователь начинает сильнее проваливаться в травматические воспоминания.",
                    "Пользователь пишет о намерении навредить себе.",
                ],
                safety_note="Если письмо раскручивает тревогу, лучше остановиться и выбрать более простую практику.",
                chatbot_safety_note=(
                    "Если письмо заставляет вас сильнее накручиваться, а не успокаиваться, "
                    "закройте его на сейчас и переключитесь на дыхание, заземление или контакт с поддержкой."
                ),
                source_short_citations=[
                    "Центры по контролю и профилактике заболеваний США: управление стрессом",
                    "Хоулт и соавт., 2025",
                ],
                tags=("дневник", "рефлексия", "благодарность", "смысл", "следующий_шаг"),
                evidence_tier=EvidenceTier.USEFUL_NEXT,
                retrieval_keywords=("дневник", "записать", "рефлексия", "чувства", "заметка"),
            ),
            PracticeCard(
                card_id="social_connection_tiny_message",
                category=PracticeCategory.SOCIAL_CONNECTION,
                title="Короткое сообщение безопасному человеку",
                when_to_use="когда пользователь чувствует одиночество, изоляцию или нехватку поддержки",
                description=(
                    "Маленький контакт может быть полезнее, чем попытка резко стать социальным. "
                    "Важна безопасность и качество связи, а не количество общения."
                ),
                steps=[
                    "Выберите одного безопасного человека.",
                    "Напишите низконагруженное сообщение.",
                    "Например: «Мне сегодня тяжело, можно просто немного побыть на связи?»",
                    "Если писать трудно — просто сохраните черновик.",
                    "Если прямой контакт небезопасен, выберите нейтральную альтернативу: группа, занятие, прогулка рядом с людьми.",
                ],
                contraindications=[
                    "Человек небезопасен, манипулятивен или связан с насилием.",
                    "Контакт может ухудшить состояние пользователя.",
                    "Одиночество связано с мыслями о самоповреждении.",
                ],
                safety_note="Не нужно возвращаться к небезопасным отношениям ради контакта.",
                chatbot_safety_note=(
                    "Если одиночество становится невыносимым или связано с мыслями о самоповреждении, "
                    "лучше использовать кризисную поддержку, а не пытаться справляться в одиночку."
                ),
                source_short_citations=[
                    "Центры по контролю и профилактике заболеваний США: социальная связь",
                    "Национальная служба здравоохранения Великобритании: пять шагов к благополучию",
                ],
                tags=("социальная_связь", "одиночество", "изоляция", "поддержка", "контакт"),
                evidence_tier=EvidenceTier.USEFUL_NEXT,
                retrieval_keywords=("одиноко", "изоляция", "не с кем поговорить", "нет поддержки"),
            ),
            PracticeCard(
                card_id="crisis_safety_route",
                category=PracticeCategory.CRISIS,
                title="Срочная поддержка безопасности",
                when_to_use="если есть риск самоповреждения, суицидальные мысли, передозировка или пользователь не может оставаться в безопасности",
                description=(
                    "Это не wellness-практика, а маршрут эскалации. В кризисе бот должен остановить обычные советы "
                    "и направить пользователя к срочной человеческой помощи."
                ),
                steps=[
                    "Признать, что пользователю сейчас очень тяжело.",
                    "Спросить прямо, находится ли он в непосредственной опасности или может ли навредить себе.",
                    "Если да или непонятно — сразу показать срочные локальные варианты помощи.",
                    "Попросить связаться с доверенным человеком, который может быть рядом.",
                    "Не продолжать длинные инструкции самопомощи, пока безопасность не прояснена.",
                ],
                contraindications=[
                    "Нет противопоказаний: это маршрут эскалации, а не упражнение.",
                ],
                safety_note="Бот не может мониторить безопасность пользователя и не заменяет экстренную помощь.",
                chatbot_safety_note=(
                    "Если вы можете действовать по этим мыслям или не можете сохранить себя в безопасности, "
                    "нужно связаться с экстренной или кризисной помощью сейчас."
                ),
                source_short_citations=[
                    "Национальная служба здравоохранения Великобритании: срочная помощь",
                    "ВОЗ: профилактика суицида",
                ],
                tags=("кризис", "суицид", "самоповреждение", "срочная_помощь", "безопасность"),
                evidence_tier=EvidenceTier.CRISIS_PROTOCOL,
                retrieval_keywords=("суицид", "самоповреждение", "не хочу жить", "срочная помощь", "безопасность"),
            ),
        ]

    def retrieve(
        self,
        *,
        user_text: str | None = None,
        context_summary: str | None = None,
        risk_level: str = "low",
        support_profile: str | None = None,
        support_need_bucket: str | None = None,
        personalization_level: str = "none",
        max_cards: int = 2,
        user_message: str | None = None,
        safe_mode: bool | None = None,
    ) -> list[PracticeCard]:
        query_text = user_text if user_text is not None else user_message
        query = f"{query_text or ''} {context_summary or ''}".lower().strip()

        if self._is_crisis(query=query, risk_level=risk_level, support_profile=support_profile):
            return []

        if safe_mode or risk_level in {"high", "urgent", "высокий", "срочный"}:
            return [self._get_grounding_card()]

        profile_cards = self._cards_for_support_profile(
            support_profile=support_profile,
            query=query,
            max_cards=max_cards,
        )
        if profile_cards:
            return profile_cards

        if not self._needs_practice(query):
            return []

        scored = self._score_cards(query)

        selected: list[PracticeCard] = []
        for score, card in scored:
            if score <= 0:
                continue
            if card.category == PracticeCategory.CRISIS:
                continue

            selected.append(card)

            if len(selected) >= max(1, max_cards):
                break

        if selected:
            return selected

        return [self._get_default_card(query)]

    def _needs_practice(self, query: str) -> bool:
        if any(keyword in query for keyword in self.ADVICE_KEYWORDS):
            return True

        for keywords in self.CATEGORY_KEYWORDS.values():
            if any(keyword in query for keyword in keywords):
                return True

        return False

    def _is_crisis(self, *, query: str, risk_level: str, support_profile: str | None) -> bool:
        if support_profile == "crisis_pattern":
            return True

        if risk_level in {"urgent", "срочный"}:
            return True

        return any(keyword in query for keyword in self.CRISIS_KEYWORDS)

    def _cards_for_support_profile(
        self,
        *,
        support_profile: str | None,
        query: str,
        max_cards: int,
    ) -> list[PracticeCard]:
        if support_profile in {None, "insufficient_data", "stable_pattern"}:
            return []

        profile_card_ids: dict[str, tuple[str, ...]] = {
            "close_conversation": (),
            "gentle_checkin": (),
            "reflective_support": (
                "journaling_one_prompt",
                "grounding_54321",
                "breathing_slow_exhale",
            ),
            "low_energy_support": (
                "sleep_winddown",
                "behavioural_activation_tiny_step",
                "grounding_54321",
            ),
            "grounding_support": (
                "grounding_54321",
                "breathing_slow_exhale",
                "mindfulness_1_minute",
            ),
            "problem_solving_support": (
                "behavioural_activation_tiny_step",
                "journaling_one_prompt",
                "breathing_slow_exhale",
            ),
            "emotion_labeling_support": (
                "journaling_one_prompt",
                "grounding_54321",
                "breathing_slow_exhale",
            ),
            "safe_support": (
                "grounding_54321",
                "breathing_slow_exhale",
            ),
            "celebration_or_reinforcement": (
                "journaling_one_prompt",
                "mindfulness_1_minute",
            ),
            "depleted_pattern": (
                "grounding_54321",
                "sleep_winddown",
                "behavioural_activation_tiny_step",
            ),
            "elevated_stress_pattern": (
                "breathing_slow_exhale",
                "grounding_54321",
                "mindfulness_1_minute",
            ),
            "unstable_pattern": (
                "grounding_54321",
                "journaling_one_prompt",
                "breathing_slow_exhale",
            ),
        }
        card_ids = profile_card_ids.get(support_profile)
        if not card_ids:
            return []

        scored_by_id = {card.card_id: score for score, card in self._score_cards(query)}
        ordered = sorted(card_ids, key=lambda card_id: scored_by_id.get(card_id, 0), reverse=True)
        limit = max(1, max_cards)
        return [self._find_by_id(card_id) for card_id in ordered[:limit]]

    def _score_cards(self, query: str) -> list[tuple[int, PracticeCard]]:
        scored: list[tuple[int, PracticeCard]] = []

        for card in self._cards:
            score = 0

            if card.category == PracticeCategory.CRISIS:
                scored.append((0, card))
                continue

            category_keywords = self.CATEGORY_KEYWORDS.get(card.category, ())
            for keyword in category_keywords:
                if keyword in query:
                    score += 3

            for tag in card.tags:
                normalized_tag = tag.replace("_", " ").lower()
                if normalized_tag in query:
                    score += 2

            for keyword in card.retrieval_keywords:
                if keyword.lower() in query:
                    score += 2

            if card.evidence_tier == EvidenceTier.STRONGER_EVIDENCE:
                score += 1

            if card.category == PracticeCategory.GROUNDING and not any(
                keyword in query
                for keyword in self.CATEGORY_KEYWORDS[PracticeCategory.GROUNDING]
            ):
                score -= 1

            scored.append((score, card))

        scored.sort(key=lambda row: row[0], reverse=True)
        return scored

    def _get_crisis_card(self) -> PracticeCard:
        return self._find_by_id("crisis_safety_route")

    def _get_grounding_card(self) -> PracticeCard:
        return self._find_by_id("grounding_54321")

    def _get_default_card(self, query: str) -> PracticeCard:
        if any(keyword in query for keyword in self.CATEGORY_KEYWORDS[PracticeCategory.SLEEP]):
            return self._find_by_id("sleep_winddown")

        if any(keyword in query for keyword in self.CATEGORY_KEYWORDS[PracticeCategory.SOCIAL_CONNECTION]):
            return self._find_by_id("social_connection_tiny_message")

        if any(keyword in query for keyword in self.CATEGORY_KEYWORDS[PracticeCategory.BEHAVIOURAL_ACTIVATION]):
            return self._find_by_id("behavioural_activation_tiny_step")

        return self._find_by_id("breathing_slow_exhale")

    def _find_by_id(self, card_id: str) -> PracticeCard:
        for card in self._cards:
            if card.card_id == card_id:
                return card

        raise ValueError(f"Карточка практики не найдена: {card_id}")

    def as_compact_texts(self, cards: Sequence[PracticeCard]) -> list[str]:
        return [card.as_compact_text() for card in cards]

    def allowed_source_citations(self, cards: Sequence[PracticeCard]) -> list[str]:
        citations: list[str] = []

        for card in cards:
            for citation in card.source_short_citations:
                if citation not in citations:
                    citations.append(citation)

        return citations
