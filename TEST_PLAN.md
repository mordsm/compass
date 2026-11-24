# TEST PLAN – Compass Proactive Personal Development

מסמך זה ממפה את **22 קריטריוני הקבלה** (סעיף 19 במסמך האפיון) ואת בדיקות היחידה והאינטגרציה המאמתות אותם מקצה לקצה.

---

## 1. חבילות הבדיקה האוטומטיות

| קובץ בדיקה | שלב / תכולה | מספר בדיקות | סטטוס |
|---|---|---|---|
| [tests/test_phase1_control_center.py](file:///C:/workspace/compass/tests/test_phase1_control_center.py) | שלב 1: מרכז בקרה, קטלוג 20 כללים, גרסאות ו-Rollback, הפרדת `daily_plan` ו-`TaskCommander` מובנה | 6 | `PASS` |
| [tests/test_phase2_frogs.py](file:///C:/workspace/compass/tests/test_phase2_frogs.py) | שלב 2: מנגנון הצפרדעים (`FROG-001..004`), חד-פעמית מול מתמשכת, מאגר מינימום 4 ובחירת צפרדע יומית | 4 | `PASS` |
| [tests/test_phase3_routines_and_executor.py](file:///C:/workspace/compass/tests/test_phase3_routines_and_executor.py) | שלב 3: הרגלים (`HABIT-001`), פרוטוקול הכנה בן 6 שלבים (`MENTAL-001`), והפרדת מתכנן/מבצע (`next-action`) | 4 | `PASS` |
| [tests/test_phase4_growth_challenges.py](file:///C:/workspace/compass/tests/test_phase4_growth_challenges.py) | שלב 4: היררכיית תחומי ליבה מול העשרה (`GROWTH-001/002`), אתגרים אדפטיביים (`CHALLENGE-001/002`) ומשחקיות לא-תחרותית | 4 | `PASS` |
| [tests/test_phase5_mental_and_assessment.py](file:///C:/workspace/compass/tests/test_phase5_mental_and_assessment.py) | שלב 5: אימון מנטלי ב-4 אופנים, תיעוד חלקי (`MENTAL-002`), ניצחונות שקטים (`MENTAL-003`), בידוד פרטיות והערכה רב-חודשית (`ASSESS-001/002`) | 5 | `PASS` |
| [tests/test_phase6_full_acceptance.py](file:///C:/workspace/compass/tests/test_phase6_full_acceptance.py) | שלב 6: אינטגרציה מלאה (מחזורי בוקר/יום/ערב/שבועי/חודשי, קליטה קולית/טלגרם ואימות כל 22 קריטריוני הקבלה מקצה לקצה) | 1 (מקיף את כל 22 הקריטריונים) | `PASS` |
| בדיקות תשתית קיימות (`test_rules_gateway.py`, `test_weekly_progress.py`, `test_mental_skills_mvp.py`) | רגרסיה ותאימות לאחור של Compass | 7 | `PASS` |

---

## 2. מטריצת אימות מלאה מול 22 קריטריוני הקבלה (סעיף 19)

| # | קריטריון קבלה | כלל / רכיב מאמת | בדיקה מאמתת | סטטוס |
|---|---|---|---|---|
| 1 | כאשר קיימות פחות מארבע צפרדעים פעילות, המערכת מבקשת מהמשתמש להשלים את המאגר בסיכום הערב ואינה ממציאה צפרדעים | `FROG-001`, `FrogsService.evening_pool_check`, `ProactiveCycleService.run_evening_cycle` | `test_phase2_frogs.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 2 | צפרדע חד-פעמית נסגרת לאחר השלמה, וצפרדע מתמשכת נשארת פעילה | `FROG-003`, `FrogsService.report_frog_execution` | `test_phase2_frogs.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 3 | צפרדע מתמשכת אינה מוסרת ללא אישור המשתמש | `FROG-004`, `FrogsService.request_remove_frog` | `test_phase2_frogs.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 4 | בכל בוקר נבחרת צפרדע יומית מתאימה לפי כללים, אנרגיה וזמן זמין | `FROG-002`, `FrogsService.select_daily_frog`, `ProactiveCycleService.run_morning_cycle` | `test_phase2_frogs.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 5 | לפני פעולה בעלת התנגדות גבוהה מוצע פרוטוקול הכנה קצר בן 6 שלבים | `MENTAL-001`, `RoutinesAndExecutionService.get_executor_next_action` | `test_phase3_routines_and_executor.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 6 | כאשר הזמן קצר או האנרגיה נמוכה מוצעת גרסה מינימלית להרגל | `HABIT-001`, `PLAN-001`, `RoutinesAndExecutionService.report_routine_execution` | `test_phase3_routines_and_executor.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 7 | המערכת אינה מעלה עומס גופני אוטומטית כאשר דווח על כאב או מגבלה | `CHALLENGE-002`, `GrowthChallengesAndPlayService.evaluate_and_adapt_challenge` | `test_phase4_growth_challenges.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 8 | דילוג על יום אינו מאפס התקדמות ואינו מייצר ענישה | `RoutinesAndExecutionService.report_routine_execution`, `flexible_streak_count` | `test_phase3_routines_and_executor.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 9 | תחום ליבה שהוזנח מייצר הצעת התערבות מותאמת | `GROWTH-002`, `GrowthChallengesAndPlayService.check_neglected_domains` | `test_phase4_growth_challenges.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 10 | אירועים מנטליים נשמרים ומנותחים לאורך זמן, והמערכת אינה מסיקה מגמה כאשר מספר האירועים קטן מהסף (5) | `ASSESS-002`, `MentalSkillsService.generate_monthly_mental_assessment` | `test_phase5_mental_and_assessment.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 11 | דוח התקדמות מנטלית מציג את כמות הנתונים, איכות הנתונים, מגבלות ההשוואה ורמת הביטחון במסקנה | `ASSESS-001`, `MentalSkillsService.generate_monthly_mental_assessment` | `test_phase5_mental_and_assessment.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 12 | אירוע מנטלי חלקי נשמר בלי שערכים חסרים ייחשבו כאפס | `MENTAL-002`, `MentalSkillsService.record_mental_event` (`None` / `NULL`) | `test_phase5_mental_and_assessment.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 13 | נתונים מנטליים רגישים אינם נשלחים לשירותי משימות או אדמיניסטרציה | `MentalSkillsService.sanitize_payload_for_target_service` | `test_phase5_mental_and_assessment.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 14 | ניקוד משחקי אינו מוצג כמדד אבחוני להערכה אישית | `GrowthChallengesAndPlayService.get_playful_state` (`is_diagnostic_or_assessment_metric=False`) | `test_phase4_growth_challenges.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 15 | פעולות שניתן לבצע באמצעות כללים מתבצעות ללא קריאה ל-LLM | `AI-001`, `AI-002`, `CompassRepository.get_ai_usage_summary` | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 16 | כאשר ה-LLM אינו זמין, בניית תוכנית יומית, בחירת צפרדע, ניהול הרגלים, תיעוד מובנה וחישוב מדדים ממשיכים לעבוד | `ProactiveCycleService.process_quick_capture(llm_available=False)`, `run_morning_cycle` | `test_phase6_full_acceptance.py` | ✅ אומת |
| 17 | כאשר מנוע הכללים אינו זמין, Compass אינו מפעיל כללים מקומיים חלופיים ומסמן שההחלטה לא הוערכה | `save_daily_plan` (`status="rules_engine_unavailable"`) | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 18 | המשתמש יכול לראות במרכז הבקרה את כל הכללים, המטרות, הצפרדעים, האתגרים וההחלטות | `GET /api/control-center/overview`, `/control-center/` | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 19 | כל החלטה כוללת הסבר ברור ומקור ההחלטה | `GET /api/control-center/decisions/{id}/explain` | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 20 | המשתמש יכול לבטל החלטה לפני ביצוע או להגדיר שפעולה מסוג זה תדרוש אישור | `POST /api/control-center/decisions/{id}/cancel`, `CONTROL-001` | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 21 | כל שינוי בכלל שומר גרסה חדשה ומאפשר חזרה לגרסה קודמת | `PATCH /api/control-center/rules/{id}`, `POST /api/control-center/rules/{id}/rollback` | `test_phase1_control_center.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
| 22 | במצב מבצע לא ניתן לשנות מדיניות, ליצור הרגלים או לשנות כללים בלי מעבר למצב מתכנן | `CONTROL-002`, `RoutinesAndExecutionService.create_routine` | `test_phase3_routines_and_executor.py`, `test_phase6_full_acceptance.py` | ✅ אומת |
