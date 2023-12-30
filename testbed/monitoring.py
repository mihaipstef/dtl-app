from datetime import (
    datetime,
    timedelta,
)
from gnuradio import testbed
import pmt
import zmq


def parse_msg(data):
    try:
        result = testbed.parse_msg(data, len(data))
        if result.encoding == testbed.msg_encoding_t.UNKNOWN:
            return {}
        if result.encoding == testbed.msg_encoding_t.PMT:
            return pmt.to_python(result.get_pmt())
        else:
            d = dict(result.get_dict())
            return d
    except Exception as e:
        print(str(e))
    return {}


def start_collect_batch(probe, db_access, batch_duration):
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.bind(probe)

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    next_batch_time = datetime.utcnow() + timedelta(milliseconds=batch_duration)

    data = []
    msg_counter = 0
    while True:
        events = poller.poll(int(batch_duration))
        for sock, _ in events:
            msg = sock.recv()
            probe_data = parse_msg(msg)
            msg_counter += 1
            if len(probe_data):
                probe_data["msg_counter"] = msg_counter
                probe_data["probe_name"] = probe_data.get("probe_name", "john_doe")
                if "time" in probe_data:
                    ts = float(probe_data["time"])
                    probe_data["time"] = datetime.utcfromtimestamp(ts/1000.0)
                data.append(db_access.prepare(probe_data))
        if (now:=datetime.utcnow()) >= next_batch_time and len(data):
            db_access.write_batch(data)
            next_batch_time = now + timedelta(milliseconds=batch_duration)
            data = []


def start_collect(probe, db_access, batch_duration):
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.bind(probe)

    msg_counter = 0
    while True:
        msg = socket.recv()

        probe_data = parse_msg(msg)
        msg_counter += 1
        if len(probe_data):
            probe_data["msg_counter"] = msg_counter
            probe_data["probe_name"] = probe_data.get("probe_name", "john_doe")
            if "time" in probe_data:
                ts = float(probe_data["time"])
                probe_data["time"] = datetime.utcfromtimestamp(ts/1000.0)
            db_access.write(probe_data)


