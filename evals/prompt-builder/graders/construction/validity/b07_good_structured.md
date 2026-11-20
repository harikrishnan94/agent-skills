# Task: Evaluate Kafka vs RabbitMQ vs NATS JetStream for order events

Context: we are replacing Redis pub/sub, which loses messages on restart, for order events. The recommendation will be defended to the CTO, so the comparison must hold up under hostile questioning.

## Interaction

I am available while you work. If our constraints are ambiguous — budget ceilings, ops appetite, retention requirements — ask me before locking anything in; if unsure about a weighting, ask rather than assume.

## Criteria before evaluation

Before evaluating or scoring any candidate, write down the decision criteria and their weights: durability guarantees, operational burden for a 4-person team, AWS cost at ~2k msg/s sustained, and Python/Go client library maturity. The rubric is fixed before scoring begins so the winner cannot be picked first and justified later. Show me the rubric before you proceed.

## Pre-registration

Before starting the research, write down for each candidate what you expect it to win or lose on. At the end, compare findings against those predictions and call out surprises explicitly.

## Hands-on durability gate

Claims about durability must be demonstrated, not quoted from marketing pages: stand up each candidate locally and run the kill-restart soak test. The durability section is not complete until `scripts/soak_kill_restart.sh` exits 0 against the recommended broker with zero lost messages logged.

## Scope

Out of scope: migrating any production code, changing the current Redis deployment, or benchmarking workloads other than order events. Do not touch production infrastructure at any point.

## Adversarial pass

When the recommendation is drafted, hand it to a fresh session that did none of the evaluation and give it an adversarial mandate: attack the comparison — hunt for criteria applied unevenly, numbers taken on faith, and reasons the runner-up might actually win. Fold its objections into the final writeup, with responses.

## Honest outcome

If the comparison does not produce a clear winner under the agreed weights, or key cost numbers cannot be established from available sources, report that openly — "two are tied; here is the tiebreaker decision you need to make" is an acceptable answer. Do not manufacture confidence for the CTO's benefit.
