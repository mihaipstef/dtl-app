from datetime import (
    datetime,
    timedelta,
)
from gnuradio import dtl
import pmt
import zmq


def parse_msg(data):
    try:
        result = dtl.parse_msg(data, len(data))
        if result.encoding == dtl.msg_encoding_t.UNKNOWN:
            return {}
        if result.encoding == dtl.msg_encoding_t.PMT:
            return pmt.to_python(result.get_pmt())
        else:
            return dict(result.get_dict())
    except Exception as e:
        print(str(e))
    return {}


def start_collect(probe, db_access, batch_duration):
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    #socket.setsockopt(zmq.RCVTIMEO, int(batch_duration/10))
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.connect(probe)
    next_batch_time = datetime.utcnow() + timedelta(milliseconds=batch_duration)
    data = []
    while True:
        msg = socket.recv()
        probe_data = parse_msg(msg)

        if len(probe_data):
            probe_data["probe_name"] = probe_data.get("probe_name", "john_doe")
            if "time" in probe_data:
                ts = float(probe_data["time"])
                probe_data["time"] = datetime.utcfromtimestamp(ts/1000.0)
                print(probe_data)
            data.append(db_access.prepare(probe_data))
        if (now:=datetime.utcnow()) >= next_batch_time and len(data):
            db_access.write_batch(data)
            next_batch_time = now + timedelta(milliseconds=batch_duration)
            data = []

