# 🧭 Compass – Proactive Personal Development
## מדריך תפעול ושימוש מלא במערכת (`SYSTEM_OPERATION_GUIDE.md`)

מסמך זה מרכז את כל הדרכים להפעיל, לתפעל ולשלוט במערכת **Compass – Proactive Personal Development** ביום-יום, בשבוע ובחודש: דרך מרכז הבקרה בדפדפן (`Control Center`), דרך קול וטלגרם (`Quick Capture`), ודרך ממשקי ה-API.

---

## 1. הפעלת המערכת וגישה למרכז הבקרה

### 1.1 הפעלת שרת Compass (כולל `rules_engine` ו-`TaskCommander` מובנים)
המערכת מריצה את מנוע הכללים (`rules_engine`) ואת מנהל המשימות התפעולי (`TaskCommander`) ישירות בתוך תהליך Compass (אפס השהיה וללא תלות ב-LLM):

```powershell
uv --directory c:\workspace\compass run uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

*(לחלופין ניתן להפעיל דרך הסקריפט הקיים: `powershell -ExecutionPolicy Bypass -File c:\workspace\compass\scripts\start_compass.ps1`)*

### 1.2 כניסה למרכז הבקרה (System Control Center)
לאחר הפעלת השרת, פתח בדפדפן:
- **מרכז הבקרה המרכזי (RTL בעברית):** `http://127.0.0.1:8080/control-center/`
- **תיעוד וניסוי ממשקי API (Swagger UI):** `http://127.0.0.1:8080/docs`

במרכז הבקרה תוכל:
1. להחליף בלחיצה בין **תפקיד מתכנן (`Planner`)** לבין **תפקיד מבצע (`Executor`)**.
2. להשהות או לחדש אוטומציה (`Pause / Resume Automation`).
3. להריץ בלחיצת כפתור את **מחזור הבוקר**, **סיכום הערב**, **הסיכום השבועי** ו**ההערכה החודשית**.
4. להזין פקודות או דיווחים מהירים בתיבת **קליטה מהירה (קול / טלגרם)**.
5. לצפות במאגר הצפרדעים, ההרגלים, פרוטוקול ההכנה (6 שלבים), תחומי הצמיחה (ליבה מול העשרה), האתגרים האדפטיביים, הניקוד המשחקי, ודוח ההתקדמות המנטלית הרב-חודשי.
6. לצפות בכל **37 הכללים בקטלוג** (כולל 20 כללי ההתפתחות הפרואקטיבית `FROG-001` עד `CONTROL-002`), להפעיל/להשבית כלל, לצפות בהיסטוריית הגרסאות שלו ולבצע `Rollback` לגרסה קודמת.
7. ללחוץ על **"הסבר"** ליד כל החלטה כדי לראות את הכלל המדויק שהופעל, הנתונים שנבדקו והכרעת ההתנגשויות, או **"בטל"** כדי לבטל החלטה לפני ביצוע.

---

## 2. שני מצבי העבודה של המשתמש: מתכנן (`Planner`) מול מבצע (`Executor`)

המערכת מפרידה באופן קשיח בין זמן קביעת המדיניות לבין זמן הביצוע היומיומי (`CONTROL-002`):

| מצב | מתי משתמשים בו? | מה מותר לעשות? |
|---|---|---|
| **מתכנן (`Planner`)** | בזמן תכנון רגוע (סוף שבוע / ערב / תחילת חודש) | הגדרת תחומי צמיחה ומטרות ארוכות טווח, יצירת הרגלים חדשים, הגדרת אתגרים ותקרת קושי, עריכת קטלוג הכללים ושינוי גבולות אוטונומיה. |
| **מבצע (`Executor`)** | במהלך היום כשרוצים לפעול בלי להתלבט | קבלת **הפעולה הבאה בלבד (`next-action`)**, הפעלת פרוטוקול הכנה קצר בן 6 שלבים לפני פעולה מאתגרת, שימוש בגרסה מינימלית של הרגל בעת עומס/אנרגיה נמוכה, ודיווח ביצוע קצר. *(במצב מבצע חסומה יצירת הרגלים או שינוי מדיניות כדי למנוע בריחה מתכנון-יתר בזמן ביצוע).* |

**מעבר בין מצבים (במרכז הבקרה או ב-API):**
```http
PATCH /api/control-center/policy
Content-Type: application/json

{
  "user_id": "moshe",
  "active_role": "executor"
}
```

---

## 3. תפעול מחזור החיים היומי, השבועי והחודשי (`/api/cycles/*`)

### 3.1 מחזור בוקר (`Morning Cycle`)
בונה תוכנית יומית מציאותית לפי רמת האנרגיה (`1–5`) והזמן הזמין בדקות:
- בוחר את **הצפרדע היומית** המתאימה ביותר לשעות הבוקר (`FROG-002`).
- משבץ הרגלים פעילים (ואם האנרגיה $\le 2$, מעביר אוטומטית לגרסה מינימלית `PLAN-001` / `HABIT-001`).
- מוודא כיסוי לתחומי הליבה (**מנטלי**, **פיזי**, **AI** – כאשר פעילות AI מספקת מכסה גם גירוי קוגניטיבי `GROWTH-001`).
- משלב אתגר פעיל ומשימות תפעוליות מ-`TaskCommander`.
- מעריך את התוכנית ב-`rules_engine`: אם התוכנית עמוסה מעבר לזמן הזמין (`PLAN-002`), היא נשמרת כ-`pending_approval` ולא מופעלת אוטומטית.

```http
POST /api/cycles/morning
Content-Type: application/json

{
  "user_id": "moshe",
  "energy_level": 4,
  "available_minutes": 180
}
```

### 3.2 מחזור תוך-יומי (`Intraday Cycle` – מצב מבצע)
מחזיר את הפעולה האחת הבאה לביצוע כעת. אם מדובר בצפרדע או בפעולה עם התנגדות גבוהה ($\ge 6$), מצרף אוטומטית את **פרוטוקול ההכנה בן 6 השלבים** (`MENTAL-001`). אם היו 2 תזכורות קודמות שלא נענו, משהה תזכורות אוטומטית למניעת הצפה.

```http
POST /api/cycles/intraday
Content-Type: application/json

{
  "user_id": "moshe",
  "energy_level": 3,
  "available_minutes": 45,
  "recent_unanswered_reminders": 0
}
```

### 3.3 מחזור ערב (`Evening Cycle`)
- מסכם משימות שהושלמו מול פתוחות ב-`TaskCommander`.
- בודק את **מאגר הצפרדעים (`FROG-001`)**: אם יש פחות מ-4 צפרדעים פעילות במאגר, מבקש ממך להשלים צפרדעים אמיתיות (**לעולם אינו ממציא צפרדעים בעצמו**).
- שומר הצלחות, קשיים והערות להקשר הבוקר של מחר.

```http
POST /api/cycles/evening
Content-Type: application/json

{
  "user_id": "moshe",
  "wins_today": ["ביצעתי אימון מתח למרות התנגדות ראשונית"],
  "difficulties_today": ["עייפות אחר הצהריים"],
  "notes_for_tomorrow": "להתחיל את הצפרדע ב-08:30"
}
```

### 3.4 מחזור שבועי (`Weekly Cycle`)
- מפיק מדדי עקביות שבועיים (`weekly_progress`).
- מזהה **תחומי ליבה שהוזנחו** מעל 7 ימים ומייצר הצעת התערבות מותאמת (`GROWTH-002`).
- מבצע בדיקת **"ניצחונות שקטים" (`Silent Wins` – `MENTAL-003`)**: מצבים שבעבר היו מעוררים תגובה אוטומטית חזקה והשבוע עברו בשקט ובבחירה.

```http
POST /api/cycles/weekly
Content-Type: application/json

{
  "user_id": "moshe",
  "silent_wins": [
    {
      "short_description": "ביקורת לא צפויה בפגישה שעברה בסקרנות ובלי התגוננות",
      "trigger_text": "ביקורת בפגישה"
    }
  ],
  "notes": "שבוע יציב בתחומי הליבה"
}
```

### 3.5 מחזור חודשי (`Monthly Longitudinal Assessment`)
- מפיק הערכת התקדמות מנטלית רב-חודשית (`ASSESS-001`, `ASSESS-002`).
- אוכף מינימום 5 אירועים מתועדים לפני הסקת מגמה (מונע מסקנות נמהרות ממדגם קטן).
- מציג בשקיפות מלאה: כמות נתונים, איכות ושלמות נתונים, מגבלות השוואה, רמת ביטחון במסקנה, אשכולות אירועים דומים (`comparable_event_clusters`), והבהרה שהמערכת אינה כלי אבחוני.
- כל הצעה לשינוי מדיניות מהותי פותחת בקשת אישור (`CONTROL-001`).

```http
POST /api/cycles/monthly
Content-Type: application/json

{
  "user_id": "moshe",
  "minimum_events_required": 5
}
```

---

## 4. קליטה מהירה בקול ובטלגרם (`Quick Capture` – Rule Engine First)

נקודת הקצה `POST /api/cycles/quick-capture` (ותיבת הקליטה המהירה במרכז הבקרה) מנתחת קודם כול פקודות בעברית באופן דטרמיניסטי (**0 טוקנים של LLM**), מתעדת בנפרד עלויות דיבור (`STT/TTS`) מעלויות `LLM` (`AI-002`), וממשיכה לעבוד באופן מלא גם כאשר ה-LLM כבוי או לא זמין (`llm_available: false`).

### פקודות קול / טלגרם מובנות נתמכות (0 טוקנים של LLM):
1. **בקשת הפעולה הבאה:**
   - `"מה הפעולה הבאה"` / `"מה עכשיו"`
2. **דיווח על צפרדע יומית:**
   - `"צפרדע בוצעה"` / `"סיימתי צפרדע"`
   - `"צפרדע בוצע חלקית"`
   - `"צפרדע נדחה"`
3. **הוספת צפרדע חדשה למאגר:**
   - `"הוסף צפרדע: תיאום בדיקת רופא"`
4. **תיעוד ניצחון שקט (`Silent Win`):**
   - `"ניצחון שקט: עצרתי לפני תגובה אוטומטית בשיחה עם לקוח"`
5. **תיעוד אירוע מנטלי מהחיים:**
   - `"אירוע מנטלי: הרגשתי דחף להתגונן מול הערה ובחרתי לשאול שאלה סקרנית"`
6. **בקשת פרוטוקול הכנה להפחתת התנגדות (6 שלבים):**
   - `"פרוטוקול הכנה"` / `"נשימה לפני פעולה"`
7. **דיווח השלמת הרגל (מלא או גרסה מינימלית):**
   - `"הרגל בוצע"` / `"הרגל בוצע גרסה מינימלית"`

---

## 5. תפעול ישיר של מנועי הליבה

### 5.1 מנגנון הצפרדעים (`Eat That Frog` – `/api/frogs/*`)
- **הוספת צפרדע (`one_time` חד-פעמית או `ongoing` מתמשכת כמו מתח/משקולות):**
  `POST /api/frogs`
- **עדכון ניקוד עצמי (חשיבות, התנגדות, קושי, דחיפות):**
  `PATCH /api/frogs/{frog_id}/scores`
- **בחירת צפרדע יומית והחלפה ידנית ע"י המשתמש:**
  `POST /api/frogs/daily-select` | `POST /api/frogs/daily-override`
- **דיווח ביצוע (`completed`, `partial`, `not_done`, `deferred`, `no_longer_resisted`):**
  `POST /api/frogs/{frog_id}/report`
  *(צפרדע חד-פעמית נסגרת אוטומטית; צפרדע מתמשכת נשארת פעילה במאגר ולא מוסרת ללא אישור מפורש שלך `FROG-004`).*

### 5.2 הרגלים, פרוטוקול הכנה והפרדת מתכנן/מבצע (`/api/routines/*`)
- **קבלת/עדכון פרוטוקול 6 השלבים להפחתת התנגדות (פתיח נעים מוגבל לעד 90 שניות):**
  `GET /api/routines/prep-protocol` | `PATCH /api/routines/prep-protocol`
- **יצירת הרגל (במצב `Planner` בלבד) עם גרסה מלאה וגרסה מינימלית (`minimum_viable_version`):**
  `POST /api/routines`
- **דיווח ביצוע או דילוג ללא ענישה (`completed`, `minimum_completed`, `skipped`):**
  `POST /api/routines/{routine_id}/report`
  *(דילוג `skipped` אינו מטיל קנס ואינו מאפס את הרצף הגמיש `flexible_streak_count`).*
- **קבלת הפעולה הבאה למצב מבצע:**
  `GET /api/routines/executor/next-action`

### 5.3 תחומי צמיחה, אתגרים אדפטיביים ומשחקיות (`/api/growth/*`)
- **צפייה ועדכון תחומי ליבה (`mental`, `physical`, `ai_professional` – משקל 10) ותחומי העשרה (`cooking`, `gardening`, `music`, `drawing` – משקל 4):**
  `GET /api/growth/domains` | `POST /api/growth/domains`
- **בדיקת תחומי ליבה שהוזנחו (`GROWTH-002`):**
  `POST /api/growth/domains/check-neglected`
- **יצירת אתגר והערכה אדפטיבית (`CHALLENGE-001/002`):**
  `POST /api/growth/challenges` | `POST /api/growth/challenges/{challenge_id}/evaluate`
  *(אם דווח `pain_or_limitation: true`, המערכת חוסמת באופן מוחלט העלאת עומס גופני אוטומטית).*
- **מצב משחקיות לא-תחרותית (מופרד לחלוטין ממדדי Assessment):**
  `GET /api/growth/playfulness`

### 5.4 אימון מנטלי פרואקטיבי והערכה רב-חודשית (`/api/msp/proactive/*`)
- **קטלוג 4 אופני האימון המנטלי (בסיס רגוע, הכנה לפני אירוע, התערבות בזמן אמת, עיבוד לאחר אירוע):**
  `GET /api/msp/proactive/catalog`
- **תיעוד אירוע מנטלי (תומך בדיווח חלקי – שדות `0–10` חסרים נשמרים כ-`NULL` ולעולם לא כ-`0`):**
  `POST /api/msp/proactive/events`
- **בדיקת ניצחונות שקטים שבועית (`Silent Wins`):**
  `POST /api/msp/proactive/silent-wins-check`
- **דוח הערכה מנטלית רב-חודשי (`ASSESS-001/002`):**
  `GET /api/msp/proactive/monthly-assessment`

### 5.5 מנהל משימות תפעולי מובנה (`TaskCommander` – `/api/task-commander/*`)
- `GET /api/task-commander/today` – משימות להיום
- `GET /api/task-commander/overdue` – משימות באיחור
- `POST /api/task-commander/tasks` – יצירת משימה (חד-פעמית או מחזורית `daily`/`weekly`)
- `POST /api/task-commander/instances/{id}/done` | `/snooze` | `/skip` – עדכון ביצוע מופע משימה

---

## 6. הרצת בדיקות האימות והקבלה (31 בדיקות אוטומטיות)

בכל עת ניתן להריץ את חבילת הבדיקות המלאה (כולל מבחן הקבלה של כל 22 קריטריוני הקבלה מקצה לקצה):

```powershell
uv --directory c:\workspace\compass run python -m unittest tests\test_phase6_full_acceptance.py tests\test_phase5_mental_and_assessment.py tests\test_phase4_growth_challenges.py tests\test_phase3_routines_and_executor.py tests\test_phase2_frogs.py tests\test_phase1_control_center.py tests\test_rules_gateway.py tests\test_weekly_progress.py tests\test_mental_skills_mvp.py -v
```
