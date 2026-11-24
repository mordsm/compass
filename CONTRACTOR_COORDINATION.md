# 🧭 בעלות פיתוח וחוזי מערכת — Antigravity כקבלן הפיתוח היחיד
## מסמך בעלות, חוזי ממשק ואינטגרציה (`CONTRACTOR_COORDINATION.md`)

**בעל המוצר ומאשר החלטות מהותיות:** המשתמש (`moshe`).  
**קבלן הפיתוח המבצע (עבור `Compass`, `rules_engine` וכלל הרכיבים המחוברים):** **`Antigravity` בלבד** (אין חלוקת עבודה מול `Codex`).  
**עדכון אחרון:** 2026-11-24

---

## 1. הבהרת בעלות ותכולה (Single Development Contractor: Antigravity)

1. **`Antigravity` הוא סוכן/קבלן הפיתוח היחיד של המערכת:** הפרויקטים `Compass` (`c:\workspace\compass`) ו-`rules_engine` (`c:\workspace\rules_engine`), וכן חיבוריהם ל-`TaskCommander` (המובנה תחת Compass), `self_manage` ו-`personal_Assessment`, מפותחים ומתוחזקים מקצה לקצה באמצעות **Antigravity**.
2. **מדוע הופיע השם `Codex` במסמך של Sharons?**
   - בעבר נוצר במאגר קובץ ישן בשם `CODEX_INSTRUCTIONS.md`, ולכן כאשר `Sharons` יצר את סעיף 27 ("תיאום קבלני פיתוח — Codex ו-Antigravity") הוא הניח בטעות שיש שני כלי פיתוח שונים שצריך לחלק ביניהם את העבודה.
   - בפועל, **אין שום צורך ב-Codex ואין שום פיצול קבלנים**: **Antigravity** כבר מימש במלואם גם את צד המדיניות ומנוע הכללים (`rules_engine`) וגם את צד הממשק, התזמון, `TaskCommander` ומרכז הבקרה (`Compass`).
3. **מקור אמת יחיד (`Single Source of Truth`):**
   - אין ולא יוקמו מנוע כללים כפול, תוכנית יומית כפולה, מאגר מטרות כפול או מאגר משימות כפול.

---

## 2. מיפוי כלל חבילות העבודה – כולן בבעלות ובמימוש Antigravity

| יכולת במערכת | מבצע | קבצים ונתיבים קנוניים במערכת | סטטוס |
|---|---|---|---|
| **1. Rules Engine, קטלוג 37 כללים, גרסאות, Rollback והכרעת התנגשויות** | **Antigravity** | `c:\workspace\rules_engine\compass_rules.py`, `c:\workspace\compass\app\services\rules_engine.py`, [RULES_CATALOG.md](file:///C:/workspace/compass/RULES_CATALOG.md) | ✅ מומש ואומת |
| **2. משימות, מופעים, תזמון ודיווח (`TaskCommander` מובנה תחת Compass – `D007`)** | **Antigravity** | [app/services/task_commander.py](file:///C:/workspace/compass/app/services/task_commander.py), [app/routers/task_commander.py](file:///C:/workspace/compass/app/routers/task_commander.py) (`tc_tasks`, `tc_task_instances`) | ✅ מומש ואומת |
| **3. תחומי התפתחות (ליבה מול העשרה), מטרות ארוכות טווח והרגלים (`HABIT-001`, `GROWTH-001/002`)** | **Antigravity** | [app/services/growth_service.py](file:///C:/workspace/compass/app/services/growth_service.py), [app/services/routines_service.py](file:///C:/workspace/compass/app/services/routines_service.py), [app/routers/growth.py](file:///C:/workspace/compass/app/routers/growth.py), [app/routers/routines.py](file:///C:/workspace/compass/app/routers/routines.py) | ✅ מומש ואומת |
| **4. תעדוף, אנרגיה, הפרדת מתכנן/מבצע (`Planner / Executor`) והפעולה הבאה (`next-action`)** | **Antigravity** | [app/routers/daily_plan.py](file:///C:/workspace/compass/app/routers/daily_plan.py), [app/services/routines_service.py](file:///C:/workspace/compass/app/services/routines_service.py) | ✅ מומש ואומת |
| **5. מנגנון הצפרדעים (`Eat That Frog`), אתגרים אדפטיביים ומשחקיות לא-תחרותית** | **Antigravity** | [app/services/frogs_service.py](file:///C:/workspace/compass/app/services/frogs_service.py), [app/routers/frogs.py](file:///C:/workspace/compass/app/routers/frogs.py), [app/services/growth_service.py](file:///C:/workspace/compass/app/services/growth_service.py) | ✅ מומש ואומת |
| **6. אימון מנטלי פרואקטיבי (4 אופנים), תיעוד חלקי (`NULL`), ניצחונות שקטים והערכה רב-חודשית (`ASSESS-001/002`)** | **Antigravity** | [app/services/mental_skills.py](file:///C:/workspace/compass/app/services/mental_skills.py), [app/routers/mental_skills.py](file:///C:/workspace/compass/app/routers/mental_skills.py) | ✅ מומש ואומת |
| **7. מחזורי בוקר, תוך-יומי, ערב, שבועי וחודשי + קליטה מהירה בקול/טלגרם (`AI-001/002`)** | **Antigravity** | [app/services/cycle_service.py](file:///C:/workspace/compass/app/services/cycle_service.py), [app/routers/cycles.py](file:///C:/workspace/compass/app/routers/cycles.py) | ✅ מומש ואומת |
| **8. System Control Center (ממשק RTL אינטראקטיבי, בונה חוקים ואייקוני `?` לכל קובייה)** | **Antigravity** | [app/routers/control_center.py](file:///C:/workspace/compass/app/routers/control_center.py), [app/static/control-center/index.html](file:///C:/workspace/compass/app/static/control-center/index.html) | ✅ מומש ואומת |

---

## 3. סטטוס אימות ו-GitHub

- **בדיקות אוטומטיות:** `Ran 31 tests in 14.311s — OK` (כל 22 קריטריוני הקבלה ב-[TEST_PLAN.md](file:///C:/workspace/compass/TEST_PLAN.md) עוברים בהצלחה).
- **מדריך תפעול:** [SYSTEM_OPERATION_GUIDE.md](file:///C:/workspace/compass/SYSTEM_OPERATION_GUIDE.md).
- **סנכרון GitHub:** שני המאגרים (`mordsm/compass` ו-`mordsm/rules_engine`) מעודכנים ומסונכרנים בענף `master`.
