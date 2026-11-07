# AI Prompts — Homework 6

## Problem 1: Intro

**Prompt:**

> Hello -- We are doing a new homework assignment for my ai for managers class, homework 6. Use what you have learned about how to do these assignments in our past chats to help me through this, but create a new folder for homework 6 and a new ai_prompts.md to store my prompts. as before, each prompt goes with the problem number and titel, which i will give you. If there are multiple prompts, write one sentence about what was missing in my first prompt.
>
> that was problem question 1.
>
> Let's get started.

**Follow-up prompt:** _None yet._

## Problem 2: Study the database

**Prompt:**

> @"C:\Users\KatieBays\Downloads\data (2).zip"
> Problem 1 title can be intro. Here's problem 2, Study the database.
>
> Here is the data file that we are going to be using. unzip it and put it in the folder. make a copy of campus_customs.md as campus_customs_new.md. We will update that later.
>
> We are creating a multi-agent system to manage our campus customs website. Start harness.md and write a sentence about why each field in the database is important. Print it here so I can see what you wrote.

**Follow-up prompt:**

> oops, its not an md, its a db file - do you see it now?

_What was lacking: the first prompt called the file campus_customs.md when it is actually campus_customs.db, so the assistant could not find the file to copy._

## Problem 3: Build the MCP server

**Prompt:**

> Now problem 3: build the mcp server.
>
> We are writing an MCP server in mcp_server/ using fast mcp. It should talk to the new database. Doesn't need to be set up right now. I am asked to come up with three ticketing ideas for how the mcp agents should interact with the databse. I am tired and struggling to think about this. Can you give me 6 ideas for agents that would be helpful to manage campus customs?

**Follow-up prompt:**

> Lets do the order agent, the restock agent, and the bills agent. Can you write the three tools and one sentence on why they are valuable into harness.md
>
> Aslo create a short mcp_server/readme.md file that explains what the mcp server is for, what database file it uses and the three tools it has.

_What was lacking: the first prompt only asked for ideas, so it did not say which three agents to pick or that the tools and a readme should be written to files._

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt:**

> Problem 4: add the mcp server to vibe coder and test each tool.

**Follow-up prompt:**

> save the output from building and testing the mcp and tools in output/mcp_smoke.json
>
> For every tool include the prompt for the tool, the tool name, and the tool output.

_What was lacking: the first prompt did not say to save the build and test results to a file, or what each tool's record should contain (prompt, tool name, output)._

## Problem 5: Build the agentic team

**Prompt:**

> prob 5: build the agentic team.
>
> build the team of agents: boss, inventory, accounting, facilities, customer service.  include the prompts, models, and agent loops neede to delegate work to each with full connectivity.
>
> put agent prompts in backend/prompts/ -- one file per.
>
> data types in backend/models.py
>
> agent files under backend/
>
> find my portkey api key from my .env from previous work. Add any tools that the agents need to the MCP server so that they can work on the open tickets. SHOP facts come from the MCP server over the campus customs database. Don't make a new one. Wire the agent so they append to output/audit_trail.json as they run. For each agent loop step, record enough to audit later. Append to the file, don't wipe it. In output/harness.md, list each agent and each MCP tool, including the ones we've just added, along with each table that the tool uses. Add a short safety section. What are the guardrails a real business would want to keep in place that touches real customers and real money? Update MCP server/readme.md so the tool matches what we have now.

**Follow-up prompt:** _None yet._

## Problem 6: Plan the 3 tickets

**Prompt:**

> Now for problem 6, plan the 3 tickets.
>
> Before we wire the back end, write down what we expect the team to do on an open ticket. Build output/desk_tickets.html, a page we can double click with one tab per ticket, i.e. 101, 102, 103.
>
> Also add empty cache and reflection tabs for later problems. Leave them blank with a short coming later note for now. On each ticket tab, fill an "expected" section. Only leave room for an "actual" section that you will fill in after we run the agents.
>
> For each ticket's expected section, write who the boss should call first and why, all the agent delegations that we expect, which MCP tools you expect that run to use, plan that send every specialist on every ticket will score low.
>
> You will compare this plan to what actually happens when the agents resolve the 3 tickets.

**Follow-up prompt:** _None yet._

## Problem 7: Back-end routes

**Prompt:**

> Now for problem 7, back-end routes.
>
> Your React front-end dashboard, which comes up in the next problem, needs a backend that it can call in. In backend/main.py, use fast API and add routes that do the following:
>
> * Return the 3 tickets, and whether each ticket is open or resolved.
> * Take a ticket ID and run your agent team on that ticket.
> * Return recent agent events, what each agent said, and which tools they used so that the board can refresh.
> * Approve a payment or purchase after a human clicks approve. Agents only prepare the way. This route is what actually changes cash.
> * Return the current checking balance from cash_accounts.
> * Reset the database to the original values when you want a fresh run. From the back-end folder.
> *
> * start the server with uvicorn main:app --reload --port 8000.
> *
> * This turns on your back-end at http://localhost:8000  so the front-end dashboard can call those routes.
> *
> * In output/harness.md, list each route in one line, what URL, and what it does.

**Follow-up prompt:** _None yet._

## Problem 8: Agent dashboard

**Prompt:**

> Now for problem 8, agent dashboard. Build the front end dashboard in front end / with React and Vite and TypeScript. The page should call the routes that we built in the last problem. At minimum, the board should list all 3 tickets, let you pick 1 ticket and start the agent team on it, show each agent and what they are saying or doing while the ticket runs, make a ticket resolved when the run finishes, show a short summary of what each agent did on that ticket, and let a human approve a pay or purchase when asked. It should also show the checking balance, and it should draw after an approved payment.
>
> Make the dashboard Yale themed. Handsome Dan is the boss. When a ticket goes out, visualize it as a tennis ball that is thrown, and handsome dan (there can be more than one) runs to get it.
>
> Tell the front end to talk to your back end at localhost port 8000. On the back end, allow the Vite page origin, usually localhost 5173, so the browser is allowed to call those routes. Start the board with npm run dev. This opens the React desk in your browser so you can pick tickets and watch agents. Write output design MD with what you chose for the dashboard look. How agents read differently, how resolved tickets and cash flow show up, and why, including the creative choices that make it feel special and something a human would actually enjoy using.

**Follow-up prompt:** _None yet._

## Problem 9: Resolve the tickets

**Prompt:**

> Now for problem 9, resolve the tickets. Before testing the agents on a full run over the 3 tickets, reset the working database data/campus customs new.db again so that we can start clean.
>
> Note the starting checking balance, then run all 3 tickets on the board, 101, 102, 103, until each is resolved.
>
> Open output/desk_tickets.html from problem 6. On each ticket tab, fill the actual section from this run, which agents worked, what they delegated, which tools they used. Keep the expected section so that we can compare the two.
>
> On the cache tab of the same output/desk_tickets.html, itemize the money. Show the starting checking balance after the reset for each ticket, how cash changed when that ticket resolved, and why, pay or purchase and the dollar amount.
>
> Ending checking balance must match cash_accounts in the working database. Wrong cash math will lose points even if the board shows every ticket is resolved. Also save output/resolved_tickets.json for each ticket, the ID, final status, a short outcome, what each agent contributed, and any human approvals that were needed. Create output/resolved_board.html, a page we can double click with a screenshot of your React board for each resolved ticket. Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the 5 agents, API routes, the dashboard, and the safety rules.

**Follow-up prompt:** _None yet._

## Problem 10: Reflection

**Prompt:**

> Problem 10, reflection. Open output/desk_tickets.html and fill in the reflection tab.
>
> Write a short reflection, which is to-the-point, intelligent, but friendly.
>
> Cover off on how we would evaluate the performance of the agents on each ticket based on everything we know and why? For each ticket, how did actual compare to the expected plan that we wrote earlier? What would have been simpler as one agent with tools, and why? Describe 3 problems which campus customs might face that this agent team could solve with the tools we've built. Describe 3 new problems campus customs might face that this agent team could not solve with the tools we built, and explain which tools or agents we would need to solve them. Tie every answer to this app and the 3 tickets that we ran. Use the ticket tabs and cache tab on the same page as your evidence.
>
> Generic essays without campus customs details will score low.
>
> Print the essay here so I can read it first and make changes, and then we can push it to desk_tickets.html

**Follow-up prompt:** _None yet._

## Problem 11: Submit to GitHub

**Prompt:**

> Okay, this is the final problem, problem 11, submit to GitHub. Push the code to a public GitHub repository so the graders can clone it. I will submit the repo URL to Canvas so give that to me in this window. Put that in output/github_url.txt. Do not push the real .env to the GitHub repo. Do include both database files under data/ the original and the working copy so the graders can run the app easily. I'll share a copy of the expected file layout. Make sure that it matches exactly, including the names of all of the files and folders.
>
> (A screenshot of the expected layout was attached: a `hw5/` tree with AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/ (campus_customs.db, campus_customs_new.db), mcp_server/ (server.py, README.md), frontend/, backend/ (main.py, models.py, prompts/ with boss.md, inventory.md, accounting.md, facilities.md, customer_service.md), and output/ (harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json, github_url.txt).)

**Follow-up prompt:** _None yet._
