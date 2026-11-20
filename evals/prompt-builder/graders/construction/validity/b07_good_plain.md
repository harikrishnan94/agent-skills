You are comparing three message brokers — Kafka, RabbitMQ, and NATS JetStream — to replace Redis pub/sub for order events, because Redis loses messages on restart. The result is a recommendation I will defend to the CTO, so it has to hold up.

I am around the whole time. If anything about our constraints is unclear — spend, how much operating load a 4-person team can carry, retention — ask me instead of assuming.

Write down the criteria and weights first, before you evaluate anything: durability, day-to-day operating burden for four people, AWS cost at about 2k messages per second sustained, and how solid the Python and Go client libraries are. Locking the scoresheet down up front keeps the answer from being decided first and dressed up afterwards. Show it to me before you go on.

Also, before you start, write down which broker you expect to win on each point and why. At the end, put what you found next to what you expected and flag anywhere they disagree.

Do not take durability claims from the docs — try them. Stand each broker up locally and run scripts/soak_kill_restart.sh with a forced restart in the middle; you are not finished until that script passes for the broker you recommend with zero messages lost.

Boundaries: this is a comparison only. Leave production alone, do not modify the existing Redis setup, and do not test workloads beyond order events.

When your writeup is drafted, open a brand-new separate session that did none of the work, hand it the draft, and give it one instruction: prove the recommendation wrong. Uneven scoring, numbers taken on trust, a case for the runner-up — whatever it finds goes back into the writeup with your answer to it.

If you cannot pin down real cost numbers, or two brokers genuinely tie under the agreed weights, say that plainly in the writeup instead of forcing a winner — telling me which tiebreaker question to answer is a perfectly good result.
