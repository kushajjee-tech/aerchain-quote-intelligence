# Recording script: analyst walkthrough (DEL-02), about 8 to 10 minutes

## Before you record (once)
1. The API account needs credit, and `.env` must contain `ANTHROPIC_API_KEY=…`. The analyst questions below call the live model, so each one costs a little.
2. The demo database is already prepared. **Do not run `make demo-prepare` again**: it resets the database and spends about $2 of API credit.
3. Start the app with `make start`, then open http://localhost:5173 in Chrome. The top bar should show **PUNE-PKG-2026** and the "Demo / evaluation RFx" badge.
4. Before you record, check that Home shows **5 of 5** responses and that Comparison shows five supplier columns.
5. Do one practice run of Part 4 without recording. Confirm each question gets an answer.

## Record
1. Press **Cmd+Shift+5**, choose "Record Selected Portion", select the browser window, then press **Record**.
2. Read the lines in quotes out loud. Type the questions exactly as written.
3. Stop with the stop button in the menu bar. The file is saved to your Desktop.

Notation: **[SCREEN]** is what should be on screen. **[pause]** is about one second. **[beat]** is a shorter pause.

---

## 0. Intro
**[SCREEN: title slide]**

"Hi, I'm Kushaj Agarwal. This is my take-home for the Senior PM role at Aerchain. It's called *Kill the Quote Spreadsheet*.
[pause]
I'll walk through the problem, how I thought about it, and then the product. Most of the time goes on the analyst conversation, because that's what the brief asked to see."

## 1. The problem
**[SCREEN: same slide]**

"A category buyer needs 30 line items of corrugated packaging, which is basically shipping boxes. They send an RFx, a request for quotes, to five vendors.
[pause]
Over the next nine days, five completely different things come back. An Excel sheet that ignores their template. A PDF priced in US dollars. A Word letter with the prices written into paragraphs. An image of a rate card. And a one-line email: '₹42 a kilo for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra.'
[beat]
The buyer spends days retyping all of that into one spreadsheet. Then the VP asks: 'What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?' That's day four, and the spreadsheet can't answer it.
[pause]
So the ask was to build the thing that ends this."

## 2. What I built
**[SCREEN: Home. Don't click.]**

"The brief reads like a typing problem. I think the real problem is trust. When crores are on the line, a fast comparison is useless if the buyer can't defend every number in it.
[pause]
So I built around three ideas.
One: **AI reads, code calculates, the buyer decides.** The AI reads the messy documents, and every value it pulls out has to quote where it came from. Plain code does every conversion and every total. No number on this screen comes from a model doing arithmetic in its head.
[beat]
Two: **uncertainty is shown, never hidden.** Every value carries a trust label. If the system isn't sure, the buyer sees it, and that value stays out of the totals until the buyer decides.
[beat]
Three: **don't guess, ask.** 'Rest same as last year': does that mean prices or terms? The system keeps both readings and drafts one precise question back to that vendor.
[pause]
Let me show you how it works."

## 3. The flow

### 3.1 Drafting
**[CLICK: Co-pilot, then the RFx drafting tab. Scroll slowly.]**

"The buyer starts from what they already have: an item list, a quality checklist, and a commercial policy. The co-pilot proposes how the item-list columns map to fields. The 30 lines are then imported exactly. The AI never retypes numbers.
[beat]
Next come the questions and the terms. Each question cites the buyer's own document. The steps run in order, and this RFx has already been through all of them. Once the conformance check passes, it goes out to the five vendors. The vendor emails are simulated from the dataset. Everything after that is live."

### 3.2 The replies
**[CLICK: Vendors & Inbox, then Sahyadri Paper Mills, then Inbox & correspondence]**

"Five replies, five formats, each kept exactly as it arrived. Here is the one-line email."

**[CLICK: back to Vendors & Inbox, then Shivam Box Works, then Documents. Point at the image name.]**

"Now a disclosure. This rate-card image is AI-generated for the demo, and the file name says so. Because it's a single uncertain read, every price from it waits for the buyer to confirm."

### 3.3 Home
**[CLICK: Home. Point at "Needs your attention". Then click Open comparison.]**

"Home shows what needs a decision first. Blockers sit at the top."

### 3.4 The email, priced
**[CLICK: a Sahyadri cell on the 5-ply line. Point at both sections. Close it.]**

"Here is the email sentence again: ₹42 a kilo for the 5-ply. Below it you can see how that became a price per box, using a documented box weight. It's marked as an assumption, because vendors bill on actual weight."

### 3.5 Dollars
**[CLICK: a Konkan cell. Point at Currency / FX. Close it.]**

"This quote was in dollars. The system converts it at the rate printed on the quote and records that step."

### 3.6 An unclear unit
**[CLICK: a Shivam cell. Point at the unit status. Close it.]**

"Shivam's rate card doesn't say whether its prices are per box, per 100 pieces or per 1000. The system won't guess a unit, so these prices stay unresolved and out of the totals. A wrong automatic fix is the worst mistake this screen could make."

### 3.7 27 of 30
**[CLICK: By supplier. Point at Malwa Corrugators, Quoted.]**

"Malwa quoted 27 of the 30 lines. The three gaps show as missing. They're never filled in."

## 4. The analyst conversation
**[CLICK: Co-pilot, then the Ask tab]**

"Now the buyer stops clicking and starts asking. I picked five questions, because a buyer has to answer each of them before awarding anything: the VP's what-if, who qualified, what's missing, what it looks like, and how much rests on assumptions."

**Q1. [TYPE]**
> What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?

*[Wait for the answer. Point at the interpretation line, then the excluded vendors. Open Caveats.]*

"That's the VP's question, word for word. First it says how it read 'cleared the quality questionnaire': the Quality section only. Then who it excluded and why. Then the total.
[beat]
Every number here comes from the award engine or from query results, and code checks each one against them. The caveats are written by code, so they can't be skipped."

**Q2. [TYPE]**
> Which vendors cleared the quality questionnaire, and why didn't the others?

*[Point at Malwa and Shivam.]*

"This matters. Unverified is not the same as failed. Malwa's ISO certificate had expired, so it's unverified. Shivam's stated capacity is 150 tons a month, which is below our minimum, so it failed that check. Calling an unverified vendor 'failed' would be unfair to them."

**Q3. [TYPE]**
> Who didn't quote everything, and what does that do to the ranking?

"Missing lines are disclosed, and the ranking shows what was actually comparable. Nothing is filled in."

**Q4. [TYPE]**
> Show unit price per box by vendor for lines 1 to 6 as a chart.

*[Point at the chart, then at the values under it. Click XLSX, then open the file.]*

"The chart is drawn only from the query result. The model never types a chart value. Dashed bars are values the system can't use as they stand. Values it's unsure about are listed underneath instead of being drawn. The table exports straight to Excel."

**Q5. [TYPE]**
> How much of that saving depends on assumptions, such as FX, reference weights, freight or last year's prices?

*[Open Sources & details, then Tool calls. Close it.]*

"This is the question a buyer with crores on the line needs answered before acting.
[beat]
Under every answer you can see which calculations ran. If a number can't be traced back to them, the answer carries a warning instead of hiding it."

## 5. Award
**[CLICK: Award. Point at the red notice and the greyed-out button.]**

"The award engine gives each line to the cheapest qualified vendor, on delivered cost where freight is known. Saving is locked, because open blockers affect this allocation. The notice names them. One is Sahyadri's answer on payment terms: 'No; 30 days credit only.'"

**[CLICK: the blocker link. This opens Review. Type the comment, then click Mark not applicable.]**

> Accept 30-day terms for this award; renegotiate at PO.

"Here the buyer knows something the documents don't, so the buyer makes the call. The reason goes straight into the audit trail."

**[CLICK: back to Award, then Save recommendation. Enter the reason. Then click Printable memo.]**

> Cheapest qualified per line; Sahyadri terms accepted for this award.

"The memo records it all: the recommendation, the lines that depend on unknown freight with their break-even point, and the decision I made. Each item traces back to its source."

## 6. Close
**[Stay on the memo.]**

"Here's what I left out on purpose: real email, a vendor portal, negotiation, and purchase orders. The flow ends at a decision the buyer can defend.
[pause]
One last thought. Building this, I came to think the interesting problem isn't reading documents. Reading is close to solved. The real problem is ambiguity. It's created when the RFx is written, and it's paid for when the replies come back.
[beat]
Fix it at both ends, with clearer RFxs and faster clarifications, and those nine days shrink.
[pause]
Thanks for watching."

---

## If something goes wrong
- An answer shows a red "not verified" banner: say "the system caught a number it couldn't verify" and move on. This is the safeguard working.
- The page is empty: check that `make start` is still running, and that RFx #1 is open.
- An answer is slow or fails: wait 30 seconds, then retry the same question once. Do not run `make demo-prepare`.
