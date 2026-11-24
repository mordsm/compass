# קטלוג כללים – Compass Proactive Personal Development (`RULES_CATALOG.md`)

קטלוג הכללים מנוהל באופן דטרמיניסטי ב-`c:\workspace\rules_engine\compass_rules.py` ונשלט דרך **System Control Center** (`/control-center/` ו-`/api/control-center/rules`).

כל שינוי בכלל (הפעלה/השבתה, שינוי עדיפות, עדכון תנאים) שומר גרסה חדשה בטבלת `rule_version_history` ומאפשר חזרה לגרסה קודמת (`POST /api/control-center/rules/{rule_id}/rollback`).

---

## 20 הכללים הראשוניים (Section 16)

| מזהה (`rule_id`) | שם הכלל | תחום (`domain`) | אירוע מפעיל (`trigger`) | עדיפות | דורש אישור | פעולה / החלטה |
|---|---|---|---|---|---|---|
| `FROG-001` | בדוק בערב אם קיימות לפחות ארבע צפרדעים | `frogs` | `evening_review.frogs_check` | 100 | לא | מבקש השלמת מאגר הצפרדעים מהמשתמש מבלי להמציא צפרדעים (`active_frogs_count < 4`) |
| `FROG-002` | בחר צפרדע מתאימה לבוקר | `frogs` | `morning_plan.select_frog`, `daily_plan.evaluate` | 95 | לא | משבץ צפרדע יומית מוקדם ביום לפי חשיבות, התנגדות, דחיפות, זמן ואנרגיה |
| `FROG-003` | הסר צפרדע חד-פעמית לאחר השלמה | `frogs` | `frog.completed` | 105 | לא | סוגר צפרדע חד-פעמית (`frog_type == "one_time"`) מהמאגר הפעיל |
| `FROG-004` | הסרת צפרדע מתמשכת דורשת אישור | `frogs` | `frog.remove_requested` | 120 | **כן** | מחייב אישור משתמש מפורש לפני הסרת צפרדע מתמשכת (`frog_type == "ongoing"`) |
| `HABIT-001` | הצע גרסה מינימלית כאשר קיימת התנגדות | `habits` | `routine.resistance_detected`, `daily_plan.evaluate` | 95 | לא | מציע גרסה מינימלית (`minimum_viable_version`) כאשר `resistance_level >= 7` |
| `MENTAL-001` | הצע הכנה קצרה לפני אירוע מאתגר | `mental` | `event.challenging_upcoming`, `frog.starting` | 95 | לא | מפעיל פרוטוקול הכנה קצר בן 6 שלבים (30–60 שניות) לפני פעולה עם התנגדות >= 6 |
| `MENTAL-002` | אפשר תיעוד מהיר לאחר אירוע | `mental` | `mental_event.occurred` | 90 | לא | פותח תיעוד מהיר (כולל דיווח חלקי כשערך חסר = `NULL` ולא `0`) |
| `MENTAL-003` | בדוק הצלחות שקטות אחת לשבוע | `mental` | `weekly_review.silent_wins_check` | 90 | לא | מזכיר לתעד מצבים שבעבר עוררו תגובה והפעם עברו בשקט (`days >= 7`) |
| `ASSESS-001` | הפק הערכה חודשית | `assessment` | `monthly_review.due` | 85 | לא | מנתב אל `personal_Assessment` להפקת דוח מגמות חודשי (`days >= 28`) |
| `ASSESS-002` | אל תסיק מגמה כשאין מספיק נתונים | `assessment` | `assessment.trend_requested` | 130 | חסימה | חוסם (`block`) הסקת מגמה כאשר מספר האירועים המתועדים קטן מ-5 |
| `GROWTH-001` | תעדף תחומי ליבה | `growth` | `daily_plan.evaluate` | 100 | לא | מתעדף פעילות בתחומי הליבה (מנטלי, פיזי, AI) על פני תחומי העשרה |
| `GROWTH-002` | זהה תחום שלא התקדם | `growth` | `growth_domain.check` | 95 | לא | מתריע ומציע התערבות כאשר תחום ליבה לא התקדם במשך 7 ימים או יותר |
| `CHALLENGE-001` | התאם אתגר לפי ביצועים ומגבלות | `challenges` | `challenge.evaluate` | 90 | לא | בוחן התקדמות/דריכה במקום ומציע התאמת קושי כשאין כאב או מגבלת בטיחות |
| `CHALLENGE-002` | אל תעלה קושי מעבר לגבולות המאושרים | `challenges` | `challenge.evaluate` | 135 | חסימה | חוסם (`block`) העלאת עומס/קושי בעת כאב, מגבלת בטיחות או חריגה מהגבול המאושר |
| `PLAN-001` | התאם תוכנית לזמן ולאנרגיה | `planning` | `daily_plan.evaluate` | 105 | לא | מתאים את התוכנית היומית לעומס מופחת כאשר `energy_level <= 2` |
| `PLAN-002` | מנע עומס מופרז | `planning` | `daily_plan.evaluate` | 125 | **כן** | שומר תוכנית כ-`pending_approval` כאשר הזמן המתוכנן עולה על הזמן הזמין |
| `AI-001` | העדף פתרון דטרמיניסטי | `ai_governance` | `ai.invocation_requested` | 130 | חסימה | חוסם (`block`) קריאת LLM כאשר קיים פתרון דטרמיניסטי |
| `AI-002` | תעד כל קריאה למודל | `ai_governance` | `ai.invocation_requested` | 100 | לא | מתעד כל קריאת LLM או STT/TTS ביומן `ai_usage_log` עם סיבה ועלות |
| `CONTROL-001` | שינוי מדיניות דורש אישור | `control` | `policy.change_requested` | 140 | **כן** | מחייב אישור משתמש מפורש לכל שינוי מהותי במדיניות או בגבולות האוטונומיה |
| `CONTROL-002` | כל החלטה משמעותית ניתנת להסבר | `control` | `decision.recorded`, `daily_plan.evaluate` | 90 | לא | מתעד כלל, גרסה, נתונים בפועל וחלופות שנבדקו ביומן ההחלטות |
