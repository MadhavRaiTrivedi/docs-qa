# Incident runbook: shipment tracking outage

Use this runbook when customers cannot see tracking updates, or the tracking API returns errors.

## Severity levels

- **SEV1**: tracking is down for all customers. Page the on-call engineer immediately and open an incident channel.
- **SEV2**: tracking is degraded or down for one region. Notify the on-call engineer within 15 minutes.
- **SEV3**: a single customer or carrier integration is affected. Create a ticket for the next working day.

## First response

1. Check the tracking API dashboard for error rate and latency.
2. Check whether the carrier webhook queue is growing. A queue above 10,000 messages means updates are not being processed.
3. If a deploy happened in the last hour, roll it back before investigating further.

## Communication

The incident commander posts an update in the status page every 30 minutes during a SEV1, and every hour during a SEV2.

## After the incident

Write a blameless post-incident review within 5 working days for every SEV1 and SEV2. The review lists the timeline, the root cause and the follow-up actions with owners.
