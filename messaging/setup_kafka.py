import os

from confluent_kafka.admin import AdminClient, NewTopic

from messaging.kafka import DEAD_TOPIC, JOBS_TOPIC, RETRY_TOPIC


def main() -> None:
    admin = AdminClient(
        {"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")}
    )
    futures = admin.create_topics(
        [NewTopic(topic, num_partitions=3, replication_factor=1) for topic in (JOBS_TOPIC, RETRY_TOPIC, DEAD_TOPIC)]
    )
    for topic, future in futures.items():
        try:
            future.result()
            print(f"created {topic}")
        except Exception as error:
            if "TOPIC_ALREADY_EXISTS" not in str(error):
                raise
            print(f"exists {topic}")


if __name__ == "__main__":
    main()
