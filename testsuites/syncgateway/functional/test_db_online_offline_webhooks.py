import time

from testkit.admin import Admin
from testkit.cluster import Cluster
from testkit.web_server import WebServer
from testkit.parallelize import *

import logging
log = logging.getLogger(settings.LOGGER)


def test_webhooks(num_users, num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset(config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(30)
    ws.stop()
    expected_events = (num_users * num_docs * num_revisions) + (num_users * num_docs)
    received_events = len(ws.get_data())
    log.info("expected_events: {} received_events {}".format(expected_events, received_events))
    assert (expected_events == received_events)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


# implements scenarios: 18 and 19
def test_db_online_offline_webhooks_offline(num_users, num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset(config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(10)

    admin.take_db_offline("db")
    time.sleep(5)
    db_info = admin.get_db_info("db")
    log.info("Expecting db state {} found db state {}".format("Offline",db_info['state']))
    assert (db_info["state"] == "Offline")

    webhook_events = ws.get_data()
    time.sleep(5)
    log.info("webhook event {}".format(webhook_events))
    last_event = webhook_events[-1]
    assert (last_event['state'] == 'offline')

    admin.bring_db_online("db")
    time.sleep(5)
    db_info = admin.get_db_info("db")
    log.info("Expecting db state {} found db state {}".format("Online", db_info['state']))
    assert (db_info["state"] == "Online")
    webhook_events = ws.get_data()
    last_event = webhook_events[-1]
    assert (last_event['state'] == 'online')
    time.sleep(10)
    log.info("webhook event {}".format(webhook_events))


    ws.stop()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


# implements scenarios: 21
def test_db_online_offline_webhooks_offline_two(num_users, num_channels, num_docs, num_revisions):

    log.info("Starting test...")
    start = time.time()

    cluster = Cluster()
    mode = cluster.reset(config_path="resources/sync_gateway_configs/sync_gateway_webhook_cc.json")

    init_completed = time.time()
    log.info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log.info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log.info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log.info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(10)

    status = cluster.servers[0].delete_bucket("data-bucket")
    assert(status == 0)

    log.info("Sleeping for 120 seconds...")
    time.sleep(120)

    webhook_events = ws.get_data()
    time.sleep(5)
    log.info("webhook event {}".format(webhook_events))
    last_event = webhook_events[-1]
    assert (last_event['state'] == 'offline')

    ws.stop()

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

