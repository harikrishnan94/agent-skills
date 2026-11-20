# Task: Evaluate and Recommend a Replacement for Redis Pub/Sub (Order Events)

## Context

You are working for a small engineering team (4 people total own all infrastructure) that currently uses Redis pub/sub to distribute order events between services. Redis pub/sub is fire-and-forget: when a subscriber disconnects or Redis restarts, in-flight messages are lost. Order events are business-critical, so this is unacceptable and the team is replacing it.

The workload: order events at roughly **2,000 messages/second sustained**, running on **AWS**. Producers and consumers are written in **Python and Go**. Assume typical order-event payloads (~1 KB JSON) unless you learn otherwise.

Three candidates are on the table, and only these three:

1. **Apache Kafka** (evaluate both self-managed on EC2 and AWS MSK, including MSK Serverless if relevant)
2. **RabbitMQ** (evaluate both self-managed and Amazon MQ for RabbitMQ; use quorum queues / streams, not classic mirrored queues)
3. **NATS JetStream** (self-managed on AWS; note if any credible managed option exists, e.g. Synadia Cloud)

## Objective

Produce a written evaluation comparing the three candidates and a single, defensible recommendation. The recommendation will be presented to and challenged by the CTO, so every load-bearing claim must be sourced or clearly labeled as an estimate/judgment call. A comparison that hand-waves or gets a durability semantics detail wrong will fail its purpose.

## Evaluation criteria (all four are required; do not add or substitute criteria)

### 1. Durability guarantees
This is the reason for the migration — treat it as the most important criterion.
- What exactly does each system guarantee about message survival across broker restart, broker crash, and single-node loss? Distinguish acknowledged-write durability (fsync/replication semantics) from replication-based durability.
- Delivery semantics available to consumers: at-least-once, at-most-once, effective exactly-once (and what caveats apply, e.g. Kafka transactions/idempotent producer, RabbitMQ publisher confirms + consumer acks, JetStream ack policies and dedup windows).
- Known failure modes and data-loss scenarios documented for each (e.g. `min.insync.replicas`/`acks` misconfiguration in Kafka, RabbitMQ classic vs quorum queue behavior, JetStream replica/RAFT behavior). Cite official documentation for each guarantee claimed.

### 2. Operational burden for a 4-person team
The team has no dedicated infra/platform engineers.
- Setup and ongoing operations: cluster sizing, upgrades, scaling, monitoring, disaster recovery, on-call surface area.
- How much does a managed offering (MSK, Amazon MQ) reduce the burden, and what does it still leave on the team (partition rebalancing, consumer lag monitoring, version upgrades, quota tuning)?
- Failure-recovery complexity: what does a 3 a.m. incident look like on each system, and what expertise does it demand?
- Be concrete: name the specific recurring tasks, not just "Kafka is operationally heavy."

### 3. AWS cost at ~2k msg/s sustained
- Build a cost model for each candidate at 2,000 msg/s sustained, ~1 KB messages (adjust if the user gives you real numbers), with whatever replication factor the durability requirement demands (assume 3x unless told otherwise) and a stated retention assumption (ask the user; default to 7 days if no answer).
- Include: instance/broker costs (name the instance types you chose and why), storage (EBS type and size), inter-AZ data transfer (this is often the dominant hidden cost — do not omit it), and managed-service pricing where applicable (MSK provisioned vs serverless, Amazon MQ instance pricing).
- Use current published AWS pricing (us-east-1 unless the user says otherwise), show your arithmetic, and state every assumption. Give a monthly USD figure or range per candidate. Precision to the dollar is not required; a defensible order-of-magnitude comparison with visible assumptions is.
- Also account for the engineering-time cost qualitatively (link to criterion 2), but keep the dollar model and the effort assessment separate.

### 4. Client library maturity for Python and Go
- For each candidate, identify the de-facto standard client(s) in Python and Go (e.g. confluent-kafka-python vs kafka-python vs aiokafka; franz-go vs sarama vs confluent-kafka-go; pika vs aio-pika; amqp091-go; nats.py; nats.go).
- Assess: maintenance activity (recent releases, open-issue responsiveness), feature completeness against the broker (does the client expose the durability controls from criterion 1 — publisher confirms, acks configuration, transactions?), async support in Python, and documentation quality.
- Flag any criterion-1 guarantee that exists in the broker but is awkward or unsupported in a mainstream Python or Go client — that gap matters more than a checkbox feature list.

## Interacting with the user

The user (the engineer commissioning this) is available to answer questions while you work. Ask early, in one or two batches — do not trickle questions one at a time, and do not stall waiting for answers.

Questions worth asking (ask only what changes the analysis):
- Message retention/replay requirements (do consumers need to replay history? how far back?)
- Ordering requirements (global order? per-order-ID order? none?)
- Peak vs sustained rate, and expected growth
- Existing AWS footprint (already in one region? Kubernetes available? Terraform?)
- Latency sensitivity, message size if not ~1 KB
- Any team familiarity with the candidates
- Budget ceiling or strong managed-vs-self-hosted preference

If the user does not respond, proceed with explicitly stated default assumptions and mark every conclusion that depends on them. Never silently invent a constraint.

## Method and evidence standards

- Research using official documentation, published AWS pricing pages, and reputable engineering sources. Every factual claim about durability semantics, pricing, or client capabilities needs a citation (URL). Blog posts and benchmarks are acceptable as supporting color, never as the sole source for a guarantee claim.
- Do not rely on vendor marketing claims for durability semantics — verify against the technical docs.
- Where the candidates are genuinely close on a criterion, say so. A comparison where one option wins every category will read as motivated reasoning to the CTO.
- Distinguish clearly between: (a) documented facts, (b) calculated estimates, (c) your judgment. Label them.

## Deliverable

A single Markdown report containing, in this order:

1. **Recommendation** (one paragraph): the pick, the two or three decisive reasons, and the strongest argument against it stated honestly.
2. **Summary comparison table**: candidates x the four criteria, with a short verdict per cell.
3. **Assumptions and open questions**: everything the analysis depends on, including which user answers (or defaults) were used.
4. **Detailed analysis per criterion** (the four sections above), with citations inline.
5. **Cost model appendix**: the full arithmetic per candidate.
6. **Anticipated CTO challenges**: 4-6 hard questions the CTO is likely to ask (e.g. "Why not just use SQS/SNS or Kinesis since we're on AWS?", "What does migration from Redis pub/sub look like?", "What happens at 10x volume?") with your prepared answers. You must address why the recommendation beats the obvious AWS-native alternatives even though they were not formal candidates — one or two paragraphs, not a fourth full evaluation.
7. **Runner-up and trigger conditions**: which candidate you'd switch to and what changed circumstance would trigger that.

## Out of scope

- Do not evaluate candidates beyond the three listed (the AWS-native question is handled only as a CTO challenge, per above).
- Do not write migration code or infrastructure-as-code; a brief migration-path sketch inside the CTO-challenges section is enough.
- Do not run benchmarks; use published numbers with citations and note their conditions.

## Success criteria

The report succeeds if: (1) it makes one clear recommendation; (2) every durability claim traces to official documentation; (3) the cost model's assumptions are visible and its arithmetic checks out, including inter-AZ transfer; (4) operational burden is assessed specifically for a 4-person team with no dedicated infra staff; (5) client maturity is assessed against the specific durability features the team must use; and (6) a skeptical CTO reading it can see where the analysis is fact and where it is judgment, and finds the counterarguments already addressed.
