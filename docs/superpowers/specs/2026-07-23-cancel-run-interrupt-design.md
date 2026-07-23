# Cancel button → LangGraph run cancel (design)

Date: 2026-07-23  
Status: approved (approach A)

## Problem

The chat UI **Cancel** button calls `stream.stop()`, which only disconnects the client stream. With `streamResumable: true` and without run-id persistence, disconnect defaults to `onDisconnect: "continue"`, so the LangGraph server keeps running the agent.

## Goal

Clicking **Cancel** must interrupt the active server run via the LangGraph API, while **keeping** partial checkpoints / streamed messages (`action=interrupt`, not `rollback`).

## Chosen approach: A

Enable SDK reconnect metadata so `stop()` issues the built-in cancel:

`POST /threads/{thread_id}/runs/{run_id}/cancel`  
(equivalent: `client.runs.cancel(threadId, runId, /* wait */ false, "interrupt")`)

### Change

In `agent-chat-ui/src/providers/Stream.tsx`, pass `reconnectOnMount: true` to `useStream`.

Effects:

1. `run_id` is stored in `sessionStorage` under `lg:stream:{threadId}`.
2. `stream.stop()` (Cancel button) reads that id and calls `client.runs.cancel`.
3. Refresh / remount can rejoin an in-flight stream (acceptable side effect; aligns with existing `streamResumable: true`).

### Non-goals

- No graph / backend code changes.
- No `rollback` cancel action.
- No custom Cancel handler that manually tracks `run_id` (approach B).
- No SDK major upgrade required for this fix.

## Acceptance

1. While a run is streaming, click **Cancel**.
2. Browser Network shows a cancel request to  
   `/threads/<thread_id>/runs/<run_id>/cancel`.
3. Server run stops; UI loading ends; already-streamed content remains.
4. Existing submit options (`streamResumable: true`, etc.) stay unchanged.

## Out of scope / follow-ups

- Explicit toast on cancel failure.
- Cancel-all-runs for a thread.
