# Recording the analyst walkthrough (DEL-02) — about 8 minutes

## Before you record (once)
1. Make sure the API account has credit and `.env` contains `ANTHROPIC_API_KEY=…`.
2. In Terminal: `cd ~/Desktop/aerchain-assignment && make demo-prepare` (about 10 minutes). It resets the database and runs the whole flow live: co-pilot draft → conformance → send → all responses read → three warm-up questions.
3. Start the app: `make start`, then open http://localhost:5173 in Chrome. Keep the RFx number at 1 (top left).
4. Check that Comparison shows five vendor columns with prices before you record.

## Record
1. Press **Cmd+Shift+5** → "Record Selected Portion" → select the browser window → **Record**.
2. Follow the script below. Speak the lines in *italics*; type the questions exactly.
3. Stop with the stop button in the menu bar. The file is saved to your Desktop.

## Script
**0. Opening (Comparison page)**
*"This is one RFx for 30 corrugated packaging SKUs, quoted by five vendors in five different formats: an Excel sheet, a USD letterhead PDF, a Word letter, a photo of a rate card, and a one-line email. Everything you see was read by the system; nothing was retyped. One disclosure: the rate-card 'photo' is an AI-generated image, labelled as such."*
Click one Sahyadri cell → the drawer shows the exact sentence "₹42/kg for the 5-ply…" and how ₹/kg became ₹/box. Close it.

**1. Analyst page.** Type:
> What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?

*"It says how it read 'cleared the quality questionnaire', which vendors it excluded and why, and the total. Every number comes from the award engine, not from the model."* Open **Caveats** and point at freight-dependent lines and exposures.

**2.** Type:
> Which vendors cleared the quality questionnaire, and why didn't the others?

*"Unverified is not the same as failed: Malwa's ISO certificate had expired, so it is unverified; Shivam's capacity is below our minimum."*

**3.** Type:
> Whose ISO 9001 certificate is valid, and until when?

*"Facts from attached documents, each with its source."* Open **Show work**.

**4.** Type:
> Show unit price per box by vendor for lines 1 to 6 as a chart.

*"The chart is drawn only from the query result. Outlined bars still need review, and values the system isn't sure of are listed below rather than drawn."* Click **xlsx** under the table and open the file.

**5.** Type:
> Who didn't quote everything, and what does that do to the ranking?

*"Missing lines are disclosed, never filled in."*

**6.** Type:
> How much of that saving depends on assumptions, such as FX, reference weights, freight or last year's prices?

*"This is what a buyer with ₹4 crore on the line needs to see before acting."*

**7. Close on the Award page.** Click **Run cheapest-per-line** → **Acknowledge and draft memo** → **Printable memo**.
*"The recommendation, the lines that depend on unknown freight with their break-even, and the readiness items I acknowledged: all traceable to source."*

## If something goes wrong
- An answer shows a red "not verified" banner: say *"the system caught a number it couldn't verify"* and move on. This is a feature.
- The page is empty: check that `make start` is still running and that RFx # is 1.
