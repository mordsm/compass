# FamilyBiz - Product Outline

FamilyBiz helps a household answer one practical question: how much money is really available, what is still expected to come in or go out, and what changed without anyone noticing.

## Tracking Income And Expenses

- Automatic collection of bank and credit-card transactions.
- Categorization of expenses into household categories.
- Ongoing tracking of spending during the month.
- Clear view of income versus expenses.
- Detection of changes in recurring bills.
- Identification of payments that increased quietly.
- Tracking bank fees, card fees, and other financial costs.
- Separation between real spending, internal transfers, savings transfers, and credit-card settlements.

## Household Cashflow

- Current available-to-spend amount until the end of the month.
- Expected income versus expected expenses.
- Upcoming credit-card charges by actual debit date.
- Forecast of the expected bank balance after known commitments.
- Distinction between spending already made and payments that will be debited later.
- Month-by-month view of what is still open, paid, or expected.
- Freshness indicator showing whether the financial picture is up to date.

## Family Budget

- Monthly household budget.
- Spending targets by category.
- Tracking budget utilization throughout the month.
- Detection of categories with overspending.
- Shared picture for partners.
- Ability to invite a partner to manage the budget together.
- Personal, partner, and shared transaction views.

## Recurring Payments And Subscriptions

- Detection of standing orders and recurring card charges.
- Detection of subscriptions such as streaming, AI tools, telecom, and apps.
- Alerts when a recurring payment becomes more expensive.
- Alerts for duplicate or unusual recurring payments.
- Reminder before a significant upcoming charge.
- Option to mark a recurring payment as income, bill, commitment, loan, rent, or subscription.

## Assets And Liabilities

FamilyBiz can combine the household picture at different levels of detail:

- Current accounts.
- Credit cards.
- Savings.
- Investment accounts.
- Loans.
- Mortgages.
- Pensions.
- Insurance policies.
- Additional financial products.

## Savings And Goals

- Tracking money moved into savings.
- Separation between money available for spending and money reserved for future goals.
- Household savings goals.
- Monthly progress toward a savings target.
- Suggested savings amount based on the current cashflow.
- Dynamic adjustment of savings suggestions when the month changes.

## Smart Alerts

- Significant drop in balance.
- Credit-card charge higher than usual.
- Unusual expense compared with previous months.
- Missing or stale financial source.
- Duplicate-looking charge.
- Bank fee or financial cost that increased.
- Budget category close to limit.

## Simple Language Summary

FamilyBiz should explain the household picture in plain language:

- What changed this month?
- What is still expected to be debited?
- How much can we spend without going into overdraft?
- Where did we exceed the usual pattern?
- Which source needs to be refreshed?
- Which payment should we check?

## Privacy And Collaboration

- Household-level view for shared decisions.
- Account-level visibility control.
- Ability to mark a transaction as mine, partner's, or shared.
- Notes and questions on a transaction.
- Manual correction of category or ownership.
- Approval flow for sensitive actions or shared financial changes.

## Positioning

FamilyBiz is not only an expense report. It is a household cashflow assistant: it connects what already happened, what is still expected, and what the family can safely decide today.

## Application Prototype

The current prototype is implemented as a responsive PWA under:

```text
app/static/familybiz
```

It can run on desktop through Compass:

```text
http://127.0.0.1:8000/familybiz/
```

On Android, open the same URL in Chrome and choose "Add to Home screen" to install it as a standalone app. The prototype includes a manifest and service worker, so it can behave like an installed app while still sharing one codebase with the desktop version.

### Remote Android Access

For a quick remote HTTPS URL:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\start-familybiz-remote.ps1
```

The script prints a Cloudflare `trycloudflare.com` URL. Open:

```text
https://printed-url.trycloudflare.com/familybiz/
```

On Android, open the URL in Chrome and choose "Add to Home screen".

Quick tunnels are temporary. For a stable family URL, create a Cloudflare named tunnel, set `CLOUDFLARE_TUNNEL_TOKEN` in `.env`, and run:

```powershell
docker compose -f deploy/docker-compose.cloudflare.yml up -d --build
```

Then use the public hostname configured in Cloudflare:

```text
https://your-compass-domain.example/familybiz/
```
