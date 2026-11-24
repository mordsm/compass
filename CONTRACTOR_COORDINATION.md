# 🤝 תיאום קבלני פיתוח (Codex & Antigravity) באמצעות Sharons Chief of Staff
## מסמך בעלות, חוזי ממשק, תלויות ומסירה (`CONTRACTOR_COORDINATION.md`)

**מקור סמכות:** נגזר מסעיף 27 באפיון Compass גרסה 6. במקרה של סתירה, האפיון המאוחד גובר.  
**מתאם אינטגרציה:** `Sharons` באמצעות `Chief of Staff`.  
**בעל המוצר ומאשר החלטות מהותיות:** המשתמש (`moshe`).  
**עדכון אחרון:** 2026-11-24

---

## 1. עקרונות תיאום ובעלות (Governance & Single Source of Truth)

1. **`Compass` ו-`rules_engine` הם רכיבי תוכנה במערכת אחת** – לא הוקמו ולא יוקמו מנוע כללים כפול, תוכנית יומית כפולה, מאגר מטרות כפול, מנגנון המלצות כפול או מאגר משימות כפול.
2. **`Antigravity` ו-`Codex` הם קבלני פיתוח מקבילים** – אינם שירותי runtime ואינם מנהלים זה את זה. שניהם פועלים תחת Backlog ותוכנית אחת שמנהל `Chief of Staff` של `Sharons`, וקוראים/מעדכנים את אותו מסמך מצב משותף ([CURRENT_STATE.md](file:///C:/workspace/compass/CURRENT_STATE.md)).
3. **שער אישורים (סעיף 21):** כל שינוי בחוזה ממשק, בסכמת מסד הנתונים המשותפת ([app/database.py](file:///C:/workspace/compass/app/database.py)) או בהתנהגות משותפת מתועד ב-[DECISIONS.md](file:///C:/workspace/compass/DECISIONS.md) ודורש סקירה ואישור משתמש.

---

## 2. מטריצת חלוקת חבילות עבודה ומצב מימוש נוכחי (Work Packages & File Ownership)

הטבלה להלן ממפה את חלוקת האחריות מסעיף 27 אל הקבצים והממשקים הממומשים בפועל במאגרים `c:\workspace\compass` ו-`c:\workspace\rules_engine`:

| חבילת יכולת | קבלן מוביל | אחריות משלימה | קבצים ונתיבים קנוניים במערכת (Single Source) | סטטוס נוכחי |
|---|---|---|---|---|
| **1. Rules Engine, קטלוג, גרסאות, הכרעת התנגשויות** | **Antigravity** | **Codex** משלב ממשק ותוצאות | `c:\workspace\rules_engine\compass_rules.py`, `c:\workspace\compass\app\services\rules_engine.py`, `c:\workspace\compass\RULES_CATALOG.md` | ✅ מומש ואומת (37 כללים פעילים כולל 20 כללי `FROG-001..CONTROL-002`, גרסאות ו-Rollback) |
| **2. משימות, מופעים, אירועים, תזמון, דיווח (`TaskCommander`)** | **Codex** | **Antigravity** מגדיר מדיניות; שימוש ב-`TaskCommander` תחת Compass (`D007`) | `c:\workspace\compass\app\services\task_commander.py`, `c:\workspace\compass\app\routers\task_commander.py` (`tc_tasks`, `tc_task_instances`) | ✅ תשתית `TaskCommander` מובנית תחת Compass מוכנה להרחבות תזמון/תצוגה של Codex |
| **3. זהות, ערכים, מטרות, הרגלים, התחייבויות** | **Antigravity** | **Codex** מספק ממשק וקליטה | `c:\workspace\compass\app\services\growth_service.py`, `c:\workspace\compass\app\services\routines_service.py`, `app/routers/growth.py`, `app/routers/routines.py` | ✅ מומש (`growth_domains`, `routines`, `HABIT-001`, `GROWTH-001/002`) |
| **4. תעדוף, אנרגיה, Context Mode, Anti-Drift, המלצות** | **Antigravity** | **Codex** אוסף נתונים, מציג ומבצע החלטות מאושרות | `c:\workspace\compass\app\routers\daily_plan.py`, `c:\workspace\compass\app\services\routines_service.py` (`get_executor_next_action`) | ✅ מומש (`PLAN-001/002`, הפרדת `proposed -> pending_approval -> active`, ו-`next-action`) |
| **5. צפרדעים, אתגרים, אימון מנטלי, משחקיות** | **Antigravity** | **Codex** מספק תצוגה, תזמון ודיווח משותפים | `app/services/frogs_service.py`, `app/services/growth_service.py`, `app/services/mental_skills.py` | ✅ מומש (`frogs`, `challenges`, `playful_engagement_state`, `msp_mental_events`, `msp_silent_win_checks`) |
| **6. סקירות יום/שבוע/חודש, Morning Intent** | **Antigravity** (תוכן וניתוח) | **Codex** (איסוף, תזמון, הצגה) | `c:\workspace\compass\app\services\cycle_service.py`, `c:\workspace\compass\app\routers\cycles.py` (`/api/cycles/morning`, `/intraday`, `/evening`, `/weekly`, `/monthly`) | ✅ מומש ומוכן לחיבור לתזמוני Codex / Telegram |
| **7. Progressive Onboarding, Inbox** | **Codex** | **Antigravity** מספק שאלות ודרישות מדיניות; מאגר אחד | טבלאות `conversation_events`, `user_autonomy_policy`, `growth_domains` ב-`c:\workspace\compass\app\database.py` | ⏳ ממתין להובלת Codex על בסיס חוזה המדיניות הקיים |
| **8. התערבויות (Interventions)** | **Antigravity** (בחירת התערבות) | **Codex** (מסירה, תקציב התראות, שעות שקט ובקרה) | בחירת התערבות: `check_neglected_domains`, `run_intraday_cycle` (`reminder_throttled`) | ✅ לוגיקת בחירת התערבות ובלימת הצפה קיימת; מסירה ושעות שקט בהובלת Codex |
| **9. PWA, Cloudflare, קול, מדיה, Offline, גיבוי ואבטחה** | **Codex** | **Antigravity** משתמש בממשקים (`AI-001/002`) | `deploy/docker-compose.cloudflare.yml`, `POST /api/cycles/quick-capture`, `ai_usage_log` | ✅ מנתח פקודות קול/טלגרם דטרמיניסטי ומדידת עלויות `STT/TTS` מול `LLM` פעילים |
| **10. Self Management, Assessment** | בעלות במערכות הקיימות | **Codex** מוביל חיבור תפעולי; **Antigravity** מגדיר צרכי הערכה ותוכן | `c:\workspace\self_manage`, `c:\workspace\personal_Assessment`, `app/services/mental_skills.py` (`generate_monthly_mental_assessment`) | ✅ כללי ההערכה (`ASSESS-001/002`) ובידוד הפרטיות מומשו |
| **11. System Control Center** | **Codex** (ממשק) | **Antigravity** (קטלוג, הסברי החלטות וגבולות מדיניות) | `app/routers/control_center.py` (`/api/control-center/*`), `app/static/control-center/index.html` (`/control-center/`) | ✅ API מלא + ממשק RTL אינטראקטיבי עם הסברי `?` ובונה חוקים פעילים |
| **12. Attention Monitor** | **Codex** (איסוף עתידי) | **Antigravity** (ניתוח והמלצות – רק לאחר אישור פרטיות) | טרם הופעל (ממתין לאישור פרטיות מפורש של המשתמש) | 🔒 מושהה עד לאישור פרטיות |

---

## 3. חוזי ממשק קנוניים בין Antigravity ל-Codex (Canonical Interface Contracts)

**גרסת חוזה נוכחית:** `v1.0` (מותאם לקוד הפעיל ב-`c:\workspace\compass` ו-`c:\workspace\rules_engine`).  
אין ליצור נתיבי API מקבילים לנתיבים הקיימים להלן:

### 3.1 מזהים אחידים (Canonical Identifiers)
- **`user_id`**: מחרוזת (ברירת מחדל: `"moshe"`).
- **`task_id` / `instance_id`**: מזהי `TaskCommander` בטבלאות `tc_tasks` (`tc_task_*`) ו-`tc_task_instances` (`tc_inst_*`).
- **`frog_id`**: מזהה צפרדע בטבלת `frogs` (`frog_*`), עם `frog_type` מסוג `"one_time"` או `"ongoing"`.
- **`routine_id`**: מזהה הרגל בטבלת `routines` (`routine_*`).
- **`challenge_id`**: מזהה אתגר בטבלת `challenges` (`chal_*`).
- **`evaluation_id` / `decision_id`**: מזהה הערכת כלל בטבלת `rule_evaluations` (`eval_*`).
- **`approval_id`**: מזהה בקשת אישור בטבלת `approval_requests` (`approval_*`).

### 3.2 חוזה אירוע מובנה ובקשת הערכת כלל (`StructuredEvent`)
- **נתיב API ב-Compass:** `POST /api/rules/events` (או קריאה פנימית `RulesEngineAdapter().evaluate_event(event)`).
- **נתיב API ב-`rules_engine`:** `POST /api/rules/evaluate`.
- **מבנה חובה:**
```json
{
  "event_id": "evt_plan_a1b2c3d4e5",
  "event_type": "daily_plan.evaluate",
  "event_version": "1.0",
  "source": "compass.daily_plan",
  "user_id": "moshe",
  "occurred_at": "2026-11-24T06:00:00Z",
  "idempotency_key": "plan_eval_2026-11-24",
  "payload": {
    "date": "2026-11-24",
    "energy_level": 3,
    "available_minutes": 180,
    "planned_minutes": 140,
    "is_overloaded": false
  },
  "metadata": {
    "dry_run": false,
    "requested_actions": []
  }
}
```

### 3.3 חוזה תוצאת הערכה והסבר החלטה (`EvaluationResult`)
- **נתיב הסבר החלטה:** `GET /api/control-center/decisions/{evaluation_id}/explain`
- **ביטול החלטה לפני ביצוע:** `POST /api/control-center/decisions/{evaluation_id}/cancel`
- **שדות תוצאה מובטחים:**
  - `evaluation_id`, `event_id`
  - `final_decision`: `"block" | "require_approval" | "allow_with_redaction" | "allow_read_only" | "allow" | "recommendation_only"`
  - `risk_level`: `"low" | "medium" | "high" | "critical"`
  - `matched_rules`: רשימת כללים שהופעלו (`rule_id`, `name`, `version`, `priority`, `effects`)
  - `alternatives_considered` ו-`conflicts_resolved`: תיעוד מלא של כללים מתחרים ואיזה כלל גבר לפי `priority` וחומרת החלטה.
  - `explanation` ו-`readable_explanation_he`: נימוק דטרמיניסטי קריא.
- **כשל בטוח (`Fail-Closed`):** המנוע אינו שולח התראות בעצמו. כאשר `rules_engine` אינו זמין, Compass מסמן `status: "rules_engine_unavailable"` ואינו מציג החלטה כאילו אושרה.

### 3.4 חוזה תוכנית יומית מוצעת מול פעילה (`Proposed vs. Active Daily Plan`)
- **נתיב API:** `POST /api/daily-plan` (או דרך `POST /api/cycles/morning`).
- **מכונת מצבים מחייבת:**
  1. התוכנית נבנית תחילה כ-מוצעת ונשלחת להערכת `daily_plan.evaluate` ב-`rules_engine` **לפני** שמירתה במסד הנתונים.
  2. אם `final_decision == "require_approval"` (למשל חריגה מזמן זמין לפי `PLAN-002`), התוכנית נשמרת בסטטוס `"pending_approval"` ונוצרת רשומה בטבלת `approval_requests`.
  3. אם `final_decision` מתיר הפעלה, התוכנית נשמרת בסטטוס `"active"` (עם התאמה אוטומטית לגרסאות קצרות כשרמת האנרגיה $\le 2$ לפי `PLAN-001`).
  4. אם `rules_engine` אינו זמין, התוכנית נשמרת בסטטוס `"rules_engine_unavailable"`.

### 3.5 חוזה Proposal ואישור משתמש (`Approval Request`)
- **נתיבי API:**
  - `GET /api/approvals` (או דרך `GET /api/control-center/overview` בשדה `pending_approvals`)
  - `POST /api/control-center/approvals/{approval_id}/decide?decision=approved|rejected`
  - `POST /api/approvals/{approval_id}/approve` | `POST /api/approvals/{approval_id}/reject`

---

## 4. כרטיס מסירה רשמי מ-Antigravity ל-Chief of Staff ול-Codex (Handoff Record)

בהתאם לנוהל המסירה בסעיף 27 ("בכל מסירה: מזהה משימה, בעלים, גרסת חוזה, commit/PR, תלויות, בדיקות, מגבלות, הוראות שילוב ופעולה הבאה"):

- **מזהה משימה:** `AGY-COMPASS-PPD-PHASES-0-TO-6`
- **בעלים מבצע:** `Antigravity` (בתיאום ואישור בעל המוצר `moshe`)
- **גרסת חוזה:** `v1.0`
- **Commits ומאגרים ב-GitHub:**
  - `rules_engine` (`https://github.com/mordsm/rules_engine.git`):
    - ענף פיתוח: `feature/proactive-personal-development`
    - ענף ראשי `master`: Commit `42ee95f` (כולל `5c410ea` ו-`727995e`)
  - `compass` (`https://github.com/mordsm/compass.git`):
    - ענף פיתוח: `feature/proactive-personal-development`
    - ענף ראשי `master`: Commit `f4055ac` (כולל `d4e004f`, `43298ab`, `af906d0`)
- **תלויות:**
  - `Compass` טוען את `c:\workspace\rules_engine\compass_rules.py` ישירות In-Process (עם גיבוי HTTP לפורט `8003`).
  - `TaskCommander` פועל באופן מובנה בתוך `Compass` (`app/services/task_commander.py`) עם תמיכה ב-Fallback לשירות חיצוני בפורט `8006` אם מופעל.
- **בדיקות וראיות אימות (31/31 עוברות בהצלחה):**
  - פקודת אימות מלאה:
    ```powershell
    uv --directory c:\workspace\compass run python -m unittest tests\test_phase6_full_acceptance.py tests\test_phase5_mental_and_assessment.py tests\test_phase4_growth_challenges.py tests\test_phase3_routines_and_executor.py tests\test_phase2_frogs.py tests\test_phase1_control_center.py tests\test_rules_gateway.py tests\test_weekly_progress.py tests\test_mental_skills_mvp.py -v
    ```
  - תוצאה: `Ran 31 tests in 14.311s — OK` (פירוט מלא ב-[TEST_PLAN.md](file:///C:/workspace/compass/TEST_PLAN.md)).
- **מגבלות ושמירת גבולות:**
  - לא הוקם מסד נתונים נפרד; כל הטבלאות נמצאות ב-[app/database.py](file:///C:/workspace/compass/app/database.py) של Compass.
  - נתונים מנטליים (`msp_mental_events`) מבודדים באמצעות `sanitize_payload_for_target_service` ואינם נחשפים לשירותים תפעוליים.
  - `Attention Monitor` לא הופעל וממתין לאישור פרטיות מפורש.
- **הוראות שילוב עבור Codex / Sharons Chief of Staff:**
  1. יש לקרוא תחילה את [CURRENT_STATE.md](file:///C:/workspace/compass/CURRENT_STATE.md), מסמך זה ([CONTRACTOR_COORDINATION.md](file:///C:/workspace/compass/CONTRACTOR_COORDINATION.md)), [RULES_CATALOG.md](file:///C:/workspace/compass/RULES_CATALOG.md) ו-[SYSTEM_OPERATION_GUIDE.md](file:///C:/workspace/compass/SYSTEM_OPERATION_GUIDE.md).
  2. בעת חיבור ממשקי PWA / Telegram / Onboarding / תזמונים חיצוניים ע"י `Codex`, יש להשתמש ישירות בנקודות הקצה הקיימות (`/api/cycles/*`, `/api/control-center/*`, `/api/frogs/*`, `/api/routines/*`, `/api/growth/*`, `/api/msp/proactive/*`, `/api/task-commander/*`) ולא ליצור טבלאות או נתיבים כפולים.
  3. לפני כל מיזוג של חבילת עבודה חדשה מענף משנה, יש להריץ את 31 הבדיקות האוטומטיות ולוודא `0` רגרסיות.
