const ils = new Intl.NumberFormat("he-IL", {
  style: "currency",
  currency: "ILS",
  maximumFractionDigits: 2,
});

const demo = {
  freshness: "תמונה חלקית",
  availableMinor: 320000,
  dailyMinor: 16000,
  daysRemaining: 20,
  bankBalanceMinor: 1240000,
  balanceDate: "2026-08-09",
  cardChargeMinor: 430000,
  cardDueDate: "2026-08-10",
  savingsMinor: 250000,
  incomeMinor: 1800000,
  variableMinor: 800000,
  projectedBalanceMinor: 810000,
  sources: [
    ["בנק", "עודכן לפני 2 ימים", "aging"],
    ["כרטיס אשראי", "עודכן היום", "fresh"],
    ["מיילים פיננסיים", "דורש רענון", "stale"],
  ],
  recurring: [
    ["מנוי תקשורת", "99.00 ₪", "חיוב חוזר"],
    ["סופרמרקט", "420.00 ₪ ממוצע", "קניות חוזרות"],
    ["שירות דיגיטלי", "25.00 ₪", "מנוי קטן"],
  ],
  budgets: [
    ["מזון", 2830, 4200],
    ["בריאות", 651, 900],
    ["תחבורה", 1038, 1200],
    ["פנאי", 1475, 1100],
    ["כלים דיגיטליים", 600, 850],
  ],
  assets: [
    ["עו״ש", 16975, "asset"],
    ["חיסכון והשקעות", 20000, "asset"],
    ["חיובי אשראי קרובים", 9892, "liability"],
    ["הלוואות", 0, "liability"],
  ],
  alerts: [
    "חיוב האשראי הקרוב משויך לפי תאריך ירידה בפועל.",
    "חיובי החודש הנוכחי ישויכו לחודש הבא אם הם יורדים אז.",
    "העברה לחיסכון תופרד מהוצאה שוטפת.",
    "מקור המיילים הפיננסיים לא טרי ודורש סנכרון.",
  ],
};

const viewTitles = {
  dashboard: "תמונת כסף להיום",
  budget: "תקציב משפחתי",
  assets: "נכסים והתחייבויות",
  alerts: "התראות ופעולות",
};

function money(minor) {
  return ils.format((minor || 0) / 100);
}

function shortDate(value) {
  if (!value) return "";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function render(data) {
  setText("freshnessText", data.freshness);
  setText("availableAmount", money(data.availableMinor));
  setText("dailyAmount", `${money(data.dailyMinor)} ליום`);
  setText("daysRemaining", `${data.daysRemaining} ימים`);
  setText("bankBalance", money(data.bankBalanceMinor));
  setText("balanceDate", `נכון ל-${shortDate(data.balanceDate)}`);
  setText("cardCharge", money(data.cardChargeMinor));
  setText("cardDueDate", `יורד ב-${shortDate(data.cardDueDate)}`);
  setText("savingsTransfer", money(data.savingsMinor));
  setText("projectedBalance", `יתרה צפויה: ${money(data.projectedBalanceMinor)}`);
  setText("incomeAmount", money(data.incomeMinor));
  setText("variableSpend", money(data.variableMinor));
  setText("savingsAmount", money(data.savingsMinor));
  setText("settlementAmount", money(data.cardChargeMinor));
  document.getElementById("cashMeterFill").style.width = `${Math.max(8, Math.min(92, data.availableMinor / 12500))}%`;

  renderSources(data.sources);
  renderRecurring(data.recurring);
  renderBudgets(data.budgets);
  renderAssets(data.assets);
  renderAlerts(data.alerts);
}

function renderSources(items) {
  const list = document.getElementById("sourceList");
  list.innerHTML = "";
  for (const [name, detail, status] of items) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${name}</strong><span>${detail}</span>`;
    li.dataset.status = status;
    list.append(li);
  }
}

function renderRecurring(items) {
  const list = document.getElementById("recurringList");
  list.innerHTML = "";
  for (const [name, amount, note] of items) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${name}</strong><span>${amount} · ${note}</span>`;
    list.append(li);
  }
}

function renderBudgets(items) {
  const list = document.getElementById("budgetBars");
  list.innerHTML = "";
  for (const [name, actual, target] of items) {
    const percent = Math.round((actual / target) * 100);
    const row = document.createElement("div");
    row.className = `budget-row ${percent > 100 ? "over" : ""}`;
    row.innerHTML = `
      <strong>${name}</strong>
      <span class="bar" aria-label="${percent}%"><span style="--value: ${Math.min(percent, 135)}%"></span></span>
      <span>${percent}%</span>
    `;
    list.append(row);
  }
}

function renderAssets(items) {
  const list = document.getElementById("assetMap");
  list.innerHTML = "";
  for (const [name, amount, kind] of items) {
    const item = document.createElement("div");
    item.className = "asset-item";
    item.dataset.kind = kind;
    item.innerHTML = `<span>${name}</span><strong>${ils.format(amount)}</strong>`;
    list.append(item);
  }
}

function renderAlerts(items) {
  const list = document.getElementById("alertsList");
  list.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${item}</strong><span>FamilyBiz זיהתה זאת מתוך תזרים ומקורות מידע.</span>`;
    list.append(li);
  }
}

function normalizeCompassResponse(payload) {
  const snapshot = payload?.evidence?.cashflow_snapshot || payload?.result?.evidence?.cashflow_snapshot || payload?.cashflow_snapshot;
  if (!snapshot) return demo;
  const settlement = snapshot.credit_card_settlements?.[0] || {};
  const freshness = snapshot.freshness || {};
  const cashflow = snapshot.cashflow || {};
  const available = snapshot.available_to_spend || {};
  const balances = snapshot.balances || {};

  return {
    ...demo,
    freshness: freshness.status === "fresh" ? "תמונה טרייה" : "תמונה חלקית",
    availableMinor: available.variable_remaining_minor ?? demo.availableMinor,
    dailyMinor: available.daily_available_minor ?? demo.dailyMinor,
    daysRemaining: available.days_remaining ?? demo.daysRemaining,
    bankBalanceMinor: balances.latest_balance_minor ?? demo.bankBalanceMinor,
    balanceDate: balances.snapshot_date ?? demo.balanceDate,
    cardChargeMinor: settlement.pending_amount_minor ?? cashflow.pending_credit_card_settlement_minor ?? demo.cardChargeMinor,
    cardDueDate: settlement.due_date ?? demo.cardDueDate,
    savingsMinor: cashflow.actual_savings_transfer_minor ?? demo.savingsMinor,
    incomeMinor: cashflow.projected_income_minor ?? demo.incomeMinor,
    variableMinor: cashflow.actual_variable_expense_minor ?? demo.variableMinor,
    projectedBalanceMinor: balances.projected_end_balance_minor ?? demo.projectedBalanceMinor,
    sources: (freshness.transaction_sources || []).map((source) => [
      `${source.source} · ${source.account_id}`,
      `${source.transaction_count || 0} תנועות · ${source.status}`,
      source.status,
    ]),
    recurring: (snapshot.recurring_candidates || []).slice(0, 4).map((item) => [
      item.merchant,
      money(item.average_amount_minor),
      item.suggested_type,
    ]),
    alerts: snapshot.plain_language_alerts?.length ? snapshot.plain_language_alerts : demo.alerts,
  };
}

async function refreshFromCompass() {
  const button = document.getElementById("refreshButton");
  const status = document.getElementById("syncStatus");
  const key = document.getElementById("apiKeyInput").value.trim();
  if (key) localStorage.setItem("familybiz_api_key", key);
  button.disabled = true;
  status.textContent = "מרענן מ-Compass...";
  try {
    const response = await fetch("/api/agents/invoke", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(key ? { authorization: `Bearer ${key}` } : {}),
      },
      body: JSON.stringify({
        agent_id: "economic_manager",
        task: "cashflow_snapshot",
        user_id: "moshe",
        context: { household_id: "moshe_household" },
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    render(normalizeCompassResponse(payload));
    status.textContent = "עודכן מ-Compass";
  } catch (error) {
    status.textContent = "נשארים במצב דמו";
  } finally {
    button.disabled = false;
  }
}

function bindNavigation() {
  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.dataset.view;
      document.querySelectorAll(".nav-tab").forEach((tab) => tab.classList.toggle("active", tab === button));
      document.querySelectorAll(".view").forEach((section) => section.classList.toggle("active", section.id === `${view}View`));
      setText("viewTitle", viewTitles[view]);
    });
  });
}

function init() {
  const savedKey = localStorage.getItem("familybiz_api_key");
  if (savedKey) document.getElementById("apiKeyInput").value = savedKey;
  bindNavigation();
  document.getElementById("refreshButton").addEventListener("click", refreshFromCompass);
  render(demo);
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  }
}

init();
