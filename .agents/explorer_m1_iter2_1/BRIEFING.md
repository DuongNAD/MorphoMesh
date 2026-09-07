# BRIEFING — 2026-09-07T04:13:30Z

## Mission
Formulate an exact line-by-line implementation blueprint for blender_addon/morphomesh/listener.py to remediate socket concurrency issues (parse error queue bypass and premature EOF socket teardown).

## 🔒 My Identity
- Archetype: Explorer
- Roles: Investigation, Synthesis
- Working directory: e:\tool\mcp\MorphoMesh\.agents\explorer_m1_iter2_1
- Original parent: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
- Milestone: Milestone 1 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / do NOT edit or create any source code files.
- Deliver exact, line-by-line implementation blueprint for listener.py.
- Enqueue parse error responses into command_queue as raw responses to preserve strict FIFO response delivery.
- Defer socket closure on client EOF until all commands queued for that client have been drained by _drain_queue.

## Current Parent
- Conversation ID: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
- Updated: 2026-09-07T04:13:30Z

## Investigation State
- **Explored paths**:
  - `blender_addon/morphomesh/listener.py` (`_client_handler`, `_drain_queue`, `_dispatch`, `stop`)
  - `tests/test_m1_adversarial_socket.py` (all 28 tests, especially `test_malformed_chaos_fuzzing_interleaving` and `test_client_half_close_shutdown_wr`)
  - `tests/test_adversarial_dispatch_m1_2.py` (24 tests)
  - `tests/test_bridge_socket_parity.py` (21 tests)
  - `tests/test_blender_bridge.py` (79 tests)
  - `reviewer_m1_2/handoff.md` and `challenger_m1_1/handoff.md`
- **Key findings**:
  - Identified root cause of Queue-Bypass Response Reordering: background reader thread previously called `client.sendall` directly upon JSON parse errors, racing ahead of pending valid commands in `command_queue`.
  - Identified root cause of Premature Socket Teardown: background reader thread broke on `recv() == b""` and called `client.close()` in `finally:`, tearing down the socket before `_drain_queue` could send responses for in-flight commands.
  - Critiqued the interim polling fix (`while time.time() - start_wait < 1.0: if not any(...): break`): discovered severe in-flight execution race condition and private attribute access on `self.command_queue.queue`. As soon as `_drain_queue` pops `(cmd, client)`, the queue becomes empty and the polling loop immediately breaks, closing the socket while `_dispatch` is still executing.
  - Designed the EOF Sentinel Queue Pattern (`{"_is_eof": True}` enqueued in `command_queue` on client handler termination): guarantees 100% deterministic FIFO lifecycle coordination where `_drain_queue` dispatches all client commands and transmits responses before closing the socket.
  - Formulated unified raw response handling supporting `_is_preformatted_response`, `_raw_response`, and `_is_raw_error` with dedicated `OSError` containment.
- **Unexplored areas**: None for this scoped task.

## Key Decisions Made
- Recommended replacing polling loop with FIFO EOF Sentinel pattern (`{"_is_eof": True}, client`) in `command_queue`.
- Recommended enqueuing parse error responses on both in-stream parse errors and EOF trailing buffer parse errors.
- Recommended adding a 16MB buffer guard (`MAX_BUFFER_SIZE`) in `_client_handler`.
- Recommended catching `OSError` explicitly in `_drain_queue` to suppress noisy disconnect errors and avoid secondary fallback writes to broken sockets.

## Artifact Index
- DISPATCH.md — Initial dispatch instructions
- BRIEFING.md — Working memory & identity
- progress.md — Liveness & heartbeat
- handoff.md — Final 5-component handoff report
