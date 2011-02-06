#
# Copyright (c) 2010 Daniel Truemper truemped@googlemail.com
#
# logsink.py 03-Feb-2011
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
#
"""
Module for aggregating spyder logs.
"""
import logging
import logging.config
import signal
import os.path

import zmq
from zmq.eventloop.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream


if os.path.isfile('logging.conf'):
    logging.config.fileConfig('logging.conf')
LOGGERS = {"default": logging.getLogger()}

LOGGERS['master'] = logging.getLogger('masterlog')
LOGGERS['worker'] = logging.getLogger('workerlog')


def log_zmq_message(msg):
    """
    Log a specific message.

    The message has the format::

        message = [topic, msg]

    `topic` is a string of the form::

        topic = "process.LEVEL.subtopics"
    """
    topic = msg[0].split(".")
    if len(topic) == 3:
        topic.append("SUBTOPIC")
    if topic[1] in LOGGERS:
        log = getattr(LOGGERS[topic[1]], topic[2].lower())
        log("%s - %s" % (topic[3], msg[1].strip()))
    else:
        log = getattr(LOGGERS['default'], topic[2].lower())
        log("%s: %s)" % (topic[3], msg[2].strip()))


def main(settings):
    """
    Initialize the logger sink.
    """

    ctx = zmq.Context()
    io_loop = IOLoop.instance()

    log_sub = ctx.socket(zmq.SUB)
    log_sub.setsockopt(zmq.SUBSCRIBE, "")
    log_sub.bind(settings.ZEROMQ_LOGGING)

    log_stream = ZMQStream(log_sub, io_loop)

    log_stream.on_recv(log_zmq_message)

    def handle_shutdown_signal(_sig, _frame):
        """
        Called from the os when a shutdown signal is fired.
        """
        log_stream.stop_on_recv()
        log_stream.flush()
        io_loop.stop()

    # handle kill signals
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    io_loop.start()

    log_stream.close()
    ctx.term()
