# @tastegraph/sdk

Browser/Node capture SDK for [TasteGraph](../). It emits behavioral signals
(view / click / like / save / dismiss) to the taste graph so ranking and agent context
reflect what each user actually responds to.

```ts
import { TasteGraph } from "@tastegraph/sdk";

const tg = new TasteGraph({
  endpoint: "https://your-tastegraph-host",
  apiKey: "your_api_key",   // sent as the X-API-Key header (per-tenant auth)
  // userId omitted -> an anonymous id is generated and persisted in localStorage
});

tg.like("asset_03");
tg.view("asset_10");
// signals are batched and flushed automatically; call tg.flush() to force a send
```

## Wire format

Each signal is POSTed as JSON to `POST {endpoint}/track`. The payload is **byte-compatible
with the Python `Signal` model** (`tastebench/tastegraph/signals/schema.py`):

```json
{
  "user_id": "anon_abc123",
  "asset_id": "asset_03",
  "action": "like",
  "weight": null,
  "timestamp": 1717171717.0,
  "session_id": "s1"
}
```

`action` ∈ `view | click | like | save | dismiss`. `weight` may be `null` (the server
applies the default weight for the action). `timestamp` is seconds since the epoch.

The canonical example lives in [`fixtures/signal.json`](fixtures/signal.json) and is
validated against the Python model by `tests/test_sdk_contract.py`, so the two languages
cannot drift.

## Develop

```bash
npm install
npm test       # vitest
npm run build  # tsup -> dist/ (ESM + CJS + d.ts)
```
