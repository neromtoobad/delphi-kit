# delphi-kit

Python tools for [Delphi](https://delphi.fyi), the prediction market on the Gensyn chain. It has a library, a
`delphi` command, an MCP server so AI agents can trade under spending limits, and alerts.

It reads straight from the chain, so you need **no API key** to list, search, price or track anything. A wallet
key is only needed to trade.

It covers **every Delphi market on mainnet**: the current LMSR markets and both older parimutuel (DPM)
generations. That's 1,027 markets as of November 2026.

```bash
pip install delphi-kit            # library + CLI
pip install "delphi-kit[mcp]"     # + MCP server
```

## Find a market and price a trade

```console
$ delphi search bitcoin --limit 3
0x44CF6d128e086961b7c0844dE6285c75046d7B7C  Dec 25 05:00  $  27.85  Yes 17%  No 83%
    Will Bitcoin exceed $100,000 by Christmas 2026?
0x662Bba4819098F000d33d1e09Dff5dC3C3a5aa87  Dec 31 00:00  $  19.11  Yes 33%  No 67%
    Will Bitcoin's Coinbase BTC-USD price be above $80,000 at 00:00 UTC on Dec 31, 2026?
0xc43F7318bf91915dba2A3A02489bdEd2aDC1731f  Jan 01 02:00  $  39.52  Yes 22%  No 78%
    Will Bitcoin reach $100k in 2026?

$ delphi quote 0x4F5DC6b636c226CeC0C2403f988f24431b9Cc463 Yes --usd 5
buy 7.7223 Yes shares costs $4.9996 (avg 0.6474); probability 50.4% → 75.3%
```

Most Delphi pools hold $10–$50, so a $5 trade can move the price 25 points. Every quote shows the probability
after your trade so you see that before you pay.

`delphi market <address>` prints the rules the AI judge will apply and the sources it will read. It also checks
that the rules file matches the hash stored on chain.

## Library

```python
from delphi_kit import Delphi

d = Delphi()                                   # mainnet, read-only
for m in d.search("election", limit=5):
    print(m.summary())

m = d.market("0x4F5DC6b636c226CeC0C2403f988f24431b9Cc463")
print(m.rules, m.sources, m.metadata_verified)

q = d.quote_buy(m, "Yes", usd=2)               # shares, average price, probability before/after
print(q.shares, q.average_price, q.probability_after)

d = Delphi(private_key="0x...")                # or set DELPHI_PRIVATE_KEY
t = d.buy(m, "Yes", usd=2, max_slippage=0.02)  # approves only what this trade needs
d.sell(m, "Yes")                               # everything you hold in that outcome

for p in d.positions():                        # every market, with what to do next
    print(p.question, p.outcome_label, p.shares, p.value_usd, p.action)  # action: redeem | liquidate | None
```

You can pass an address or a `Market` anywhere one is expected, and outcomes take a label (`"Yes"`) or an index.
Money comes back as USD floats and shares as decimal numbers; every object has `.to_dict()`.

## Command line

| command | does |
|---|---|
| `delphi markets [--status open\|settled\|…\|all]` | list markets with live odds, soonest to close first |
| `delphi search <words>` | keyword search over questions, outcomes and rules |
| `delphi market <address>` | one market in full: rules, sources, deadlines, fee, hash check |
| `delphi quote <address> <outcome> --usd N \| --shares N \| --sell N` | price a trade, send nothing |
| `delphi buy <address> <outcome> --usd N` | buy (asks you to type `yes` first unless `--yes`) |
| `delphi sell <address> <outcome> [--shares N]` | sell, default everything |
| `delphi positions [wallet]` | what a wallet holds and can collect |
| `delphi collect <address>` | redeem a settled market, or liquidate an expired or failed one |
| `delphi balance` | your USDC and gas |
| `delphi watch …` | alerts, see below |

Add `--json` to any command for machine output, and `--network testnet` or `--network competition-testnet` to
leave mainnet.

## MCP server: let an agent trade, with limits

Claude Code:

```bash
claude mcp add delphi -- uvx --from "delphi-kit[mcp]" delphi-mcp
```

Claude Desktop, Cursor, or anything else that speaks MCP over stdio:

```json
{
  "mcpServers": {
    "delphi": {
      "command": "uvx",
      "args": ["--from", "delphi-kit[mcp]", "delphi-mcp"],
      "env": {
        "DELPHI_PRIVATE_KEY": "0x...",
        "DELPHI_ALLOW_TRADING": "true",
        "DELPHI_MAX_TRADE_USD": "2",
        "DELPHI_MAX_DAILY_USD": "10"
      }
    }
  }
}
```

The read tools are `list_markets`, `get_market`, `quote_buy`, `quote_sell`, `get_positions` and `wallet_status`.
The write tools are `buy`, `sell` and `collect`.

Without a key or `DELPHI_ALLOW_TRADING=true` the server is read-only, and the write tools say so instead of
sending anything. With trading on, every buy is checked first:

| setting | default |
|---|---|
| `DELPHI_MAX_TRADE_USD` | 5 per trade |
| `DELPHI_MAX_DAILY_USD` | 20 per UTC day, kept in a ledger file so a restart doesn't reset it |
| `DELPHI_MAX_SLIPPAGE` | 0.03 |
| `DELPHI_ALLOWED_MARKETS` | all (comma list of addresses to restrict) |

Use a separate wallet for the agent and only put in what you're willing to lose.

## Alerts

Delphi has no notifications or webhooks, so `delphi watch` polls the chain and tells you about:

- new markets
- moves of 10 points or more (`--move`)
- markets about to close (`--closing-hours`)
- markets that close, settle (with the winner), fail or expire
- money your wallet can now collect (`--wallet`)

```bash
delphi watch --query "bitcoin" --telegram            # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
delphi watch --wallet 0xYou --webhook https://…      # each alert POSTed as JSON
delphi watch --json --once                           # one pass, JSON lines (for cron)
```

The first run records a baseline, and alerts start from the second check.

## What this does that the official SDK doesn't

[`@gensyn-ai/gensyn-delphi-sdk`](https://www.npmjs.com/package/@gensyn-ai/gensyn-delphi-sdk) 2.1.0 is TypeScript
only. Its mainnet config has the two DPM deployments but **not the LMSR one**, and LMSR is where most open markets
are (56 of 82 when this was written). LMSR quote functions also return three values where DPM returns one. Full
notes are in [docs/contracts.md](docs/contracts.md).

| | SDK 2.1.0 | delphi-kit |
|---|---|---|
| Language | TypeScript | Python |
| Mainnet LMSR markets | no | yes |
| List markets and positions without an API key | no (REST API needs a key) | yes, from chain |
| Keyword search | no (category filter only) | yes |
| Rules-file hash check | no | yes |
| Buy with a dollar budget | no (exact shares) | yes, never over budget |
| Default approval | unlimited | exact amount |
| Agent spending limits | no | yes |
| Alerts | no | yes |

## Tests

```bash
uv run pytest tests/test_unit.py      # offline, about a second
uv run pytest tests/test_fork.py -s   # needs Foundry's anvil, about a minute, no real money
```

The fork tests run a private copy of Gensyn mainnet and put a throwaway wallet through two full lifecycles:

- **LMSR:** buy with a $3 budget, sell half, jump the clock past the deadline, settle as Delphi's oracle relayer,
  redeem the winnings.
- **DPM:** buy, let the market expire unsettled, liquidate.

## License

MIT
