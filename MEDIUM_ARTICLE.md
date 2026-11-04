# Building a Stock Research Agent That Checks Its Own Work: Five Agent Patterns in One LangGraph Project

### How I turned a stock question into a plan, three parallel workers, a critic and a memory, then deployed it on free tiers

**By Muhammad Zainurrahman**  
*8 min read*

<!-- IMAGE 1: HERO COVER BANNER -->
<!-- Place the AlphaDesk screenshot here: chat on the left, agent trace on the right -->
<!-- Caption: AlphaDesk answering "Quick read on AMZN valuation". The right panel shows the plan, the tool calls and the critic's verdict as they happen. -->

### Introduction: why a single LLM call is not an agent

Most agent demos work the same way. A user types a question, one model call runs, and some text comes back. That is fine for a chatbot, but it hides every decision that matters in a real system. Which data did the model look at? Did it make up a number? What happens when a data source fails?

A short video on agent design made the gap clear to me. It listed five patterns that separate a basic agent from one worth putting in a portfolio: tool use, reflection, plan and execute, orchestrator and worker, and memory with context management. I already had a stock alert bot called AlphaSwarm, so I rebuilt the idea around those five patterns and called the result AlphaDesk.

AlphaDesk is a small research desk. You ask a question about a stock. A planner splits it into steps, workers fetch prices, technical indicators, fundamentals and headlines, a writer drafts a short note, and a critic checks the note against the collected data before you see it. It remembers your risk profile and watchlist between sessions. It does not place trades and it does not give advice.

I kept the scope at what one person can build, explain in an interview and run for free. The frontend is on Vercel, the backend is on Render, and the language models are free ones from OpenRouter with Gemini as the last fallback.

### 1. The five patterns and where each one lives

Each pattern maps to one part of the code, which makes the design easy to point at.

| Pattern | Where it lives in AlphaDesk |
|---|---|
| Tool use | Four tools over yfinance: price snapshot, technicals, fundamentals and news |
| Plan and execute | A planner turns the question into one to six typed steps |
| Orchestrator and worker | The graph sends each step to a technical, fundamental or news worker, in parallel |
| Reflection | A critic checks the draft against the evidence and sends it back at most twice |
| Memory and context | A conversation thread, a SQLite store for watchlist and risk profile, and a trimmed context window |

<!-- IMAGE 2: ARCHITECTURE DIAGRAM -->
<!-- Place the graph diagram from ARCHITECTURE.md here -->
<!-- Caption: The agent graph. The planner fans out to workers, the writer runs once after all of them finish, and the critic can loop back to the writer. -->

The whole flow is a LangGraph state graph. The wiring is short enough to read in one piece:

```python
g.add_edge(START, "load_memory")
g.add_edge("load_memory", "planner")
g.add_conditional_edges("planner", nodes.orchestrate, ["technical", "fundamental", "news", "writer"])
for w in ("technical", "fundamental", "news"):
    g.add_edge(w, "writer")  # the writer runs once, after all parallel workers finish
g.add_edge("writer", "critic")
g.add_conditional_edges("critic", nodes.after_critic, ["writer", "save_memory"])
g.add_edge("save_memory", END)
```

The orchestrator is not a node that does work. It is a conditional edge that returns one `Send` for each planned step, so LangGraph runs the matching workers in parallel and merges what they return through a list reducer on `state.findings`.

### 2. Tools that never raise

The model never touches the market directly. It calls four small functions, and each of them returns a plain dictionary. When something goes wrong, the function returns `{"error": "..."}` instead of raising an exception. That one rule matters more than it looks. A worker that receives an error can say the data was unavailable, and the final note can say so as well. A tool that crashes takes the whole request with it.

Results are cached for ten minutes, so a follow-up question does not call the data provider again. Each worker may call at most three tools, which keeps a confused model from looping.

### 3. The critic: checking a report against its evidence

The reflection step is the part I enjoyed building most. After the writer produces a draft, the critic runs two kinds of checks. The first is a set of rules written in plain Python: every number in the draft must appear in the tool evidence, the draft must not tell the reader to buy or sell, and it must contain a risks section. The second is one more model call that reviews the draft against the evidence.

The number check is simple on purpose:

```python
def ungrounded_numbers(draft: str, findings: list) -> list[float]:
    """Numbers in the draft that do not appear (within rounding) in the tool evidence."""
    evidence = numbers(json.dumps([f.evidence for f in findings], default=str))
    bad = []
    for x in numbers(draft):
        if (x == int(x) and 0 <= abs(x) <= 10) or x in WINDOWS or (x == int(x) and 1990 <= x <= 2100):
            continue
        if not any(abs(abs(x) - abs(y)) <= max(0.011, 0.005 * abs(y)) for y in evidence):
            bad.append(x)
    return list(dict.fromkeys(bad))
```

If the critic finds a problem, the writer receives the issues and rewrites the note. The loop stops after two revisions. If a problem remains, the answer still goes out, with a line saying that some figures could not be fully verified. I preferred a visible warning to a silent failure.

The rules need care. In an early live run the critic flagged the number 70. The writer had mentioned the usual RSI overbought level, which is a convention and not data. I added the RSI thresholds of 30 and 70 to the list of indicator settings that the check ignores. Without that fix the loop would burn extra model calls on a false alarm.

### 4. Free models in order, Gemini last

The project runs on free models, and free models are unreliable. They get rate limited, they time out and sometimes they return an empty answer or broken JSON. Instead of trusting one of them, the language model layer tries a list of OpenRouter models in order and moves to the next on any failure:

```python
def run(messages, stats, tools=None, accept=None):
    for url, key, model in _providers():      # free OpenRouter models first, Gemini last
        last = url == config.GEMINI_URL
        if not last and _cool.get(model, 0) > time.time():
            continue                          # skip a model that just failed
        for attempt in range(2 if last else 1):
            try:
                msg = _post(url, key, model, messages, tools)
                out = accept(msg) if accept else msg   # accept() may reject bad JSON
                stats.ok(model)
                return out
            except Exception as e:
                if not last:
                    _cool[model] = time.time() + COOLDOWN
    raise LLMUnavailable("all models failed")
```

The `accept` callback is what makes structured output practical. The planner and critic must return JSON that fits a schema. If a model returns something that does not validate, the layer treats it like any other failure and tries the next model. Every answer reports which model produced it, so the interface can show "Answered by" and how many models were skipped.

### 5. Memory without extra model calls

Memory works at three levels. A LangGraph checkpointer keeps the conversation thread, so a follow-up such as "and what about its valuation?" resolves to the right ticker. A small SQLite database stores the risk profile, the watchlist and a one-line summary of each past analysis. Before each prompt, only the last six messages are included, each cut to 400 characters, along with at most five stored summaries.

The summary comes from the writer's closing "TL;DR" line, so memory costs no extra model call. That matters when a free tier limits how many calls you can make in a minute.

### 6. Results: eight questions on a free stack

I ran eight questions through the real graph with a script, on one machine and with free models only. Gemini was never needed.

| # | Question | LLM calls | Seconds | Revisions | Numbers not in the evidence |
|---|---|---|---|---|---|
| 1 | Is NVDA overextended right now? | 11 | 92.7 | 1 | 0 |
| 2 | Compare AAPL and MSFT for a conservative investor | 15 | 82.7 | 0 | 0 |
| 3 | What changed for TSLA this week? | 5 | 74.4 | 0 | 0 |
| 4 | Give me a quick read on AMZN valuation | 5 | 27.9 | 0 | 0 |
| 5 | Is JPM cheap relative to its fundamentals? | 5 | 85.7 | 0 | 0 |
| 6 | Technical outlook for META in one paragraph | 5 | 72.2 | 0 | 0 |
| 7 | What about its valuation? (follow up to question 1) | 7 | 66.5 | 1 | 0 |
| 8 | Tell me about the stock ZZZZQ (invalid ticker) | 9 | 34.3 | 0 | 0 |

All eight produced a report. The invalid ticker ended with a plain note that no data was available, not with an error. The median was six model calls and about 73 seconds per answer, with a range of five to fifteen calls and 28 to 93 seconds. The critic sent two of the eight first drafts back for a revision, and the follow up question in the same thread worked as intended.

The last column needs a careful reading. It counts numbers in the final report that are missing from the data the tools returned, and a script checks it. It tells you the report stays faithful to the collected data. It does not tell you that the data itself is correct. The answer quality compared with a human analyst was not measured, and these timings come from a single run on shared free models, so they will vary.

### 7. What broke after deployment

Everything above worked on my laptop. Deploying it found four problems, and each one taught me something.

The first was a dependency conflict. My pinned `langchain-core` version contradicted the pinned `langgraph` version, which only showed up when I installed from the requirements file into a clean environment. Render then picked Python 3.14, which has no prebuilt `pydantic-core` wheel, so I pinned Python 3.11 in the repository.

The second was a blank page on the Vercel site. The backend URL had a trailing slash, which produced a request to `//memory/...`, a 404 response without a watchlist, and a React component that crashed on the missing field. The frontend now strips trailing slashes and validates the memory response.

The third was the most interesting. From Render's shared IP address, Yahoo Finance accepted price requests but rejected fundamentals with a rate limit error. Prices, indicators and news kept working, and the note correctly said that valuation data was unavailable. That was honest but not useful. As a fallback, the fundamentals tool now computes P/E, profit margin, revenue growth and debt to equity from SEC EDGAR filings, which need no API key. I compared the fallback with Yahoo on seven large companies. Trailing P/E matched for all seven. Profit margin matched for six and was 36.1% against 34.6% for JPMorgan. Revenue growth and debt to equity use different definitions, such as year to date growth and long term debt only, so the tool states those definitions in its output. There is no forward P/E on this path.

The fourth was simpler. A missing environment variable on Render meant that only Gemini was being tried, and Gemini was busy. I made the model list a default in the code and added the reason for each failed model to the error message, so the next problem is easier to diagnose.

On the live site, a valuation question for Amazon now returns a trailing P/E of 21.76 and a profit margin of 16.9%. One slow run on the deployed site took 162 seconds with one revision and eleven model calls, so the free tier can be slow when models are busy.

### 8. Conclusion: what I would tell another junior engineer

Building the five patterns taught me a few things that a tutorial does not.

Tools should return errors as data. That one choice let the system degrade honestly when Yahoo blocked a request, because the worker, the writer and the critic all saw the failure and wrote around it.

A critic is only as good as its checks. A model reviewing a model is useful, but a cheap rule that compares numbers against evidence caught problems that a prose review could easily have missed. It also needs tuning, as the RSI example showed.

Free infrastructure is a design constraint, not an excuse. Caps on steps, tool calls and revisions, a cooldown for failing models and an in-memory rate limiter are what keep a free key from running out in a minute.

What I would do next is move memory to a hosted database so it survives redeploys, add a small answer set labelled by someone who knows the domain, and add authentication if the project ever stops being a demo.

### Technical stack

* Agent framework: LangGraph (state graph, `Send` for parallel workers, in-memory checkpointer)
* Language models: OpenRouter free models in order, Gemini 3.8 Flash as the last fallback
* Market data: yfinance for prices, technicals and news, SEC EDGAR as the fundamentals fallback
* Backend: FastAPI with Server-Sent Events, SQLite for memory, deployed on Render
* Frontend: React, Vite and Tailwind CSS, deployed on Vercel
* Testing: pytest with a scripted fake model and fixture data, plus an eight question demo set

### Credits and continuity

* Live demo: [alpha-desk-seven.vercel.app](https://alpha-desk-seven.vercel.app/) (the free backend can take about 50 seconds to wake up)
* Source code on GitHub: [github.com/MuhZainur/AlphaDesk](https://github.com/MuhZainur/AlphaDesk)
* LinkedIn: [linkedin.com/in/muhammad-zainurrahman](https://www.linkedin.com/in/muhammad-zainurrahman/)

AlphaDesk reads public data and writes research notes. It is not financial advice and it never places trades.

*Tags: `#AIAgents` `#LangGraph` `#LLM` `#FastAPI` `#MachineLearning`*
