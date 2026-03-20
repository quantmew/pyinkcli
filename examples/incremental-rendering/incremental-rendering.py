"""incremental-rendering example aligned with JS Ink."""

from __future__ import annotations

import random
import threading
import time
from datetime import datetime

from pyinkcli import Box, Text, render, useApp, useInput, useWindowSize
from pyinkcli.hooks import useEffect, useState

ROWS = [
    "Server Authentication Module - Handles JWT token validation, OAuth2 flows, and session management across distributed systems",
    "Database Connection Pool - Maintains persistent connections to PostgreSQL cluster with automatic failover and load balancing",
    "API Gateway Service - Routes incoming HTTP requests to microservices with rate limiting and request transformation",
    "User Profile Manager - Caches user data in Redis with write-through policy and invalidation strategies",
    "Payment Processing Engine - Integrates with Stripe, PayPal, and Square APIs for transaction processing",
    "Email Notification Queue - Processes outbound emails through SendGrid with retry logic and delivery tracking",
    "File Storage Handler - Manages S3 bucket operations with multipart uploads and CDN integration",
    "Search Indexer Service - Maintains Elasticsearch indices with real-time document updates and reindexing",
    "Metrics Aggregation Pipeline - Collects and processes telemetry data for Prometheus and Grafana dashboards",
    "WebSocket Connection Manager - Handles real-time bidirectional communication for chat and notifications",
    "Cache Invalidation Service - Coordinates distributed cache updates across Redis cluster nodes",
    "Background Job Processor - Executes async tasks via RabbitMQ with dead letter queue handling",
    "Session Store Manager - Persists user sessions in DynamoDB with TTL and cross-region replication",
    "Rate Limiter Module - Enforces API quotas using token bucket algorithm with Redis backend",
    "Content Delivery Network - Serves static assets through Cloudflare with edge caching and GZIP compression",
    "Logging Aggregator - Streams application logs to ELK stack with structured JSON formatting",
    "Health Check Monitor - Performs periodic service health checks with circuit breaker pattern implementation",
    "Configuration Manager - Loads environment-specific settings from Consul with hot reload capability",
    "Security Scanner Service - Runs automated vulnerability scans and dependency checks on deployed applications",
    "Backup Orchestrator - Schedules and executes automated database backups with encryption and versioning",
    "Load Balancer Controller - Manages NGINX upstream servers with health-based traffic distribution",
    "Container Orchestration - Coordinates Docker container lifecycle via Kubernetes with auto-scaling policies",
    "Message Bus Coordinator - Routes events through Apache Kafka topics with guaranteed delivery semantics",
    "Analytics Data Warehouse - Aggregates business metrics in Snowflake with incremental ETL processes",
    "API Documentation Service - Generates and serves OpenAPI specs with interactive Swagger UI",
    "Feature Flag Manager - Controls feature rollouts using LaunchDarkly with user targeting and percentage rollouts",
    "Audit Trail Logger - Records all user actions and system events for compliance and security analysis",
    "Image Processing Pipeline - Resizes and optimizes uploaded images using Sharp with multiple format outputs",
    "Geolocation Service - Resolves IP addresses to geographic coordinates using MaxMind GeoIP2 database",
    "Recommendation Engine - Generates personalized content suggestions using collaborative filtering algorithms",
]

ACTIONS = [
    "PROCESSING",
    "COMPLETED",
    "UPDATING",
    "SYNCING",
    "VALIDATING",
    "EXECUTING",
]


def _locale_time_string() -> str:
    return datetime.now().strftime("%I:%M:%S %p").lstrip("0")


def generate_log_line(index: int, value: int) -> str:
    action = random.choice(ACTIONS)
    throughput = f"{random.random() * 1000:.0f}"
    memory = f"{random.random() * 512:.1f}"
    cpu = f"{random.random() * 100:.1f}"
    return (
        f"[{_locale_time_string()}] Worker-{index} {action}: Batch={value} "
        f"Throughput={throughput}req/s Memory={memory}MB CPU={cpu}%"
    )


def progress_bar(value: int) -> str:
    filled = value // 5
    empty = 20 - filled
    return ("█" * filled) + ("░" * empty)


def incremental_rendering_example():
    app = useApp()
    _, terminal_height = useWindowSize()

    available_lines = max(terminal_height - 15, 10)
    log_line_count = max(int(available_lines * 0.3), 3)
    service_count = min(max(int(available_lines * 0.7), 5), len(ROWS))

    selected_index, set_selected_index = useState(0)
    timestamp, set_timestamp = useState(_locale_time_string())
    counter, set_counter = useState(0)
    fps, set_fps = useState(0)
    progress1, set_progress1 = useState(0)
    progress2, set_progress2 = useState(0)
    progress3, set_progress3 = useState(0)
    random_value, set_random_value = useState(0)
    log_lines, set_log_lines = useState(
        [generate_log_line(index, 0) for index in range(log_line_count)]
    )

    def sync_log_lines():
        if len(log_lines) == log_line_count:
            return None

        set_log_lines(
            log_lines[:log_line_count]
            if len(log_lines) >= log_line_count
            else log_lines
            + [
                generate_log_line(index, 0)
                for index in range(len(log_lines), log_line_count)
            ]
        )
        return None

    useEffect(sync_log_lines, (log_line_count, len(log_lines)))

    def clamp_selection():
        if selected_index >= service_count:
            set_selected_index(max(service_count - 1, 0))
        return None

    useEffect(clamp_selection, (service_count, selected_index))

    def setup_clock():
        running = True

        def run():
            while running:
                time.sleep(1)
                set_timestamp(_locale_time_string())
                set_counter(lambda previous: previous + 1)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_clock, ())

    def setup_rapid_updates():
        running = True

        def run():
            frame_count = 0
            last_time = time.time()

            while running:
                time.sleep(0.016)
                set_progress1(lambda previous: (previous + 1) % 101)
                set_progress2(lambda previous: (previous + 2) % 101)
                set_progress3(lambda previous: (previous + 3) % 101)
                set_random_value(random.randint(0, 999))

                def update_logs(previous):
                    if not previous:
                        return previous

                    new_lines = list(previous)
                    update_index = random.randrange(len(new_lines))
                    new_lines[update_index] = generate_log_line(
                        update_index,
                        random.randint(0, 999),
                    )
                    return new_lines

                set_log_lines(update_logs)

                frame_count += 1
                now = time.time()
                if now - last_time >= 1:
                    set_fps(frame_count)
                    frame_count = 0
                    last_time = now

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def cleanup():
            nonlocal running
            running = False

        return cleanup

    useEffect(setup_rapid_updates, ())

    def on_input(input_char, key):
        if key.up_arrow:
            set_selected_index(
                lambda previous: service_count - 1 if previous == 0 else previous - 1
            )
            return

        if key.down_arrow:
            set_selected_index(
                lambda previous: 0 if previous == service_count - 1 else previous + 1
            )
            return

        if input_char == "q":
            app.exit()

    useInput(on_input)

    visible_rows = ROWS[:service_count]

    return Box(
        Box(
            Box(
                Text(
                    "Incremental Rendering Demo - incrementalRendering=true",
                    bold=True,
                    color="cyan",
                ),
                Text(
                    f"Use ↑/↓ arrows to navigate • Press q to quit • FPS: {fps}",
                    dim_color=True,
                ),
                Text(
                    "Time: ",
                    Text(timestamp, color="green"),
                    " • Updates: ",
                    Text(str(counter), color="yellow"),
                    " • Random: ",
                    Text(str(random_value), color="cyan"),
                ),
                Text(
                    "Progress 1: ",
                    Text(progress_bar(progress1), color="green"),
                    f" {progress1}%",
                ),
                Text(
                    "Progress 2: ",
                    Text(progress_bar(progress2), color="yellow"),
                    f" {progress2}%",
                ),
                Text(
                    "Progress 3: ",
                    Text(progress_bar(progress3), color="red"),
                    f" {progress3}%",
                ),
                flexDirection="column",
            ),
            borderStyle="round",
            borderColor="cyan",
            paddingX=2,
            paddingY=1,
        ),
        Box(
            Box(
                Text(
                    "Live Logs (only 1-2 lines update per frame):",
                    bold=True,
                    color="yellow",
                ),
                *[Text(line, color="green") for line in log_lines],
                flexDirection="column",
            ),
            borderStyle="single",
            borderColor="yellow",
            paddingX=2,
            paddingY=1,
            marginTop=1,
        ),
        Box(
            Text(
                f"System Services Monitor ({service_count} of {len(ROWS)} services):",
                bold=True,
                color="magenta",
            ),
            *[
                Text(
                    f"{'> ' if index == selected_index else '  '}{row}",
                    color="blue" if index == selected_index else "white",
                )
                for index, row in enumerate(visible_rows)
            ],
            borderStyle="single",
            borderColor="gray",
            paddingX=2,
            paddingY=1,
            marginTop=1,
            flexGrow=1,
            flexDirection="column",
        ),
        Box(
            Text(
                "Selected: ",
                Text(visible_rows[selected_index], bold=True, color="magenta"),
            ),
            borderStyle="round",
            borderColor="magenta",
            paddingX=2,
            marginTop=1,
        ),
        flexDirection="column",
        height="100%",
    )


if __name__ == "__main__":
    render(
        incremental_rendering_example,
        incremental_rendering=True,
        interactive=True,
    ).wait_until_exit()
