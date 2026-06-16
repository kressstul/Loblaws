# Leadership presentation script - Loblaw Discount Division case

This script is written as a polished talk track for a 15-minute leadership presentation. Use it as a guide rather than reading it word-for-word.

## Slide 1 - Title page

Good morning / afternoon, and thank you for the opportunity to present.

Today I will walk through a 2020 performance review of the Loblaw Discount Division, using the case data provided. The focus is on what the numbers suggest about divisional performance, where leadership attention should go first, and what immediate actions I would recommend.

I will keep the main story focused, and I have included the SQL task answers and supporting analysis in the appendix for reference.

## Slide 2 - Agenda

I will cover four areas.

First, I will start with the executive takeaway: the division grew in 2020, but the market grew faster, which created a share challenge.

Second, I will walk through the performance scorecard across sales, promo, and e-commerce.

Third, I will identify the priority focus areas, especially Ontario and RCSS.

Finally, I will close with recommended actions and KPIs, then use the appendix for the SQL task and supporting detail.

## Slide 3 - Discount Division 2020: growth masked share loss

The headline is that 2020 was not a demand problem. The Discount Division delivered $25.4B in sales and grew 6.8% year over year.

However, the broader industry grew 11.0%, so the division did not keep pace with the market. As a result, national share declined from 18.0% to 17.3%, a decline of 0.7 pts.

That changes how I would frame the management question. I would not frame this as "how do we create demand?" The market was already growing. I would frame it as "how do we capture our fair share of demand?"

My recommendation is to focus on three areas: first, recover share in Ontario, particularly RCSS Ontario; second, close the e-commerce penetration gap; and third, maintain value credibility without relying only on broad-based promotions.

## Slide 4 - Scorecard: growth was strong, relative capture weaker

This scorecard explains why I believe the issue is relative capture rather than weak demand.

On sales, Discount grew 6.8%, while the industry grew 11.0%. That gap explains the share decline.

On promotion, Discount promo penetration was 35.2%, essentially in line with the national industry. Promo penetration also came down from 36.1% in 2019. So I would be cautious about making "promote more" the default answer. The data does not suggest that the division was materially under-promoted versus the market.

On e-commerce, the division grew rapidly, with e-commerce sales up 207%. But penetration was 4.6%, compared with 5.0% for the industry. That suggests the division participated in online growth, but may not have captured its full fair share.

The key takeaway for leadership is that the response should be targeted: recover share where the gap is largest, improve e-commerce execution, and use promotions surgically rather than broadly.

## Slide 5 - Focus areas: Ontario/RCSS priority; Atlantic playbook

The regional view shows where I would focus leadership attention first.

Ontario is the clearest priority. The region grew only 2.9%, and share declined about -1.0 pts. Within Ontario, the banner-level split is important: No Frills Ontario grew 6.3%, while RCSS Ontario declined -9.6%.

That suggests Ontario is not uniformly weak. The issue appears more concentrated in RCSS Ontario, so that is where I would start the diagnostic.

I would look at store-level sales, traffic versus basket, category performance, price perception, out-of-stocks, local competitor intensity, and e-commerce fulfillment constraints.

At the same time, Atlantic is a positive outlier. No Frills Atlantic grew 38.4% and gained share. I would treat Atlantic as a playbook to study: what did the team do well, and what can be transferred to other markets?

## Slide 6 - Immediate actions and KPIs

Based on the analysis, I would organize the response into four workstreams.

First, an Ontario share reset. I would start with RCSS Ontario and diagnose whether the issue is traffic, basket, price perception, assortment, availability, or local competitive pressure. The KPIs would be weekly Ontario share, RCSS Ontario sales growth, traffic, basket size, and category-level gaps.

Second, e-commerce capacity and reliability. Since e-commerce penetration trails the industry, I would look at slot availability, substitutions, online out-of-stocks, fulfillment rates, cancellations, and repeat online shoppers. The objective is to make sure we are not losing online baskets because the customer experience cannot keep up with demand.

Third, value and promo discipline. Because promo penetration is already in line with industry, I would not recommend blanket promotional depth as the first move. I would focus on key value items, targeted offers, and margin-aware promotions.

Fourth, scale what works. Atlantic appears to be outperforming, so I would study the operating model, local execution, and competitive context there, then identify which practices can be replicated.

The next data cuts I would request are margin, store count, sales per store, traffic, basket size, loyalty retention, price index, and e-commerce fulfillment metrics.

## Slide 7 - Thank you

Thank you. I will pause here and welcome questions.

If helpful, I can also go into the appendix, which includes the SQL task answers and the supporting analysis behind the recommendation.

## Slide 8 - Appendix: SQL task answers

This slide addresses the SQL task from the case instructions.

For the first question, average weekly sales for Maxi in 2020 were $61.5M per week.

For promo penetration by industry market, the results were: Atlantic 35.5%, National 35.2%, Ontario 33.5%, Quebec 33.1%, and West 35.5%.

For the highest e-commerce week, all discount markets peaked on WE Mar 14 20, with the division total at $30.4M.

For the No Frills Ontario third-week question, the logic is to rank weeks within each month. The example from the prompt is April: WE Apr 18 20, with 2019 sales of $118.8M.

For the No Frills Ontario market share question on WE Jun 27 20, the result is 9.6%, calculated as $115.6M divided by $1.21B.

## Slide 9 - Appendix: supporting analysis files

This final appendix slide provides the audit trail.

The supporting analysis file documents assumptions, key outputs, and the regional scorecard. The metric summary provides the calculated KPIs in CSV format. The SQL file includes the query logic for each SQL task question. The source workbook is also included, along with the script used to regenerate the PDF, HTML preview, talking points, and appendices.

The main assumption to highlight is that I used the total division row to avoid double-counting banner rows, and I mapped banners to the closest regional industry market for share calculations.
