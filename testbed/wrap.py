import enum
import pmt


class PortDir(enum.Enum):
    IN = 0
    OUT = 1


class PortType(enum.Enum):
    MSG = 0
    STREAM = 1


class HierPort(object):
    wrapped = None
    id = None
    owner = None

    def __init__(self, wrapped, id, owner):
        self.id = id
        self.wrapped = wrapped
        self.owner = owner


class Port(object):

    def __init__(self, id, tb, owner, wrapped, dir, t, sz = None):
        self.id = id
        self.dir = dir
        self.t = t
        self.sz = sz
        self.tb = tb
        self.owner = owner
        self.wrapped = wrapped
        assert(t == PortType.MSG or (t == PortType.STREAM and sz is not None))

    def __rshift__(self, rho):

        if type(rho) is D:
            rp = self.inp[0]
            assert(self.t == PortType.STREAM)
            assert(rp.t == PortType.STREAM)
            assert(rp.sz == self.sz)
            assert(rp.dir != self.dir)
        elif type(rho) is Port:
            rp = rho
        else:
            # Assume hier_block
            rp = HierPort(rho, 0, rho)

        if self.t == PortType.MSG:
            self.tb.msg_connect(self.wrapped, self.id, rp.wrapped, rp.id)
        elif self.t == PortType.STREAM:
             self.tb.connect((self.wrapped, self.id), (rp.wrapped, rp.id))
        if type(rho) is Port:
            return rho.owner
        return rho


class D(object):

    exclude = set(["__class__"])

    def __init__(self, tb, block_cls, *args, **kwargs):
        self.wrapped = block_cls(*args, **kwargs)
        self.inp = []
        self.outp = []

        def make_proxy(name):
            def proxy(self):
                return getattr(self.wrapped, name)
            return proxy

        for name in dir(block_cls):
            if name not in self.exclude:
                setattr(self, name, make_proxy(name))

        if ((ports_in:=getattr(self.wrapped, "message_ports_in", None))
            and ports_in is not None and callable(ports_in)):
            for p in pmt.to_python(ports_in()):
                setattr(self, p, Port(p, tb, self, self.wrapped, PortDir.IN, PortType.MSG))

        if ((ports_out:=getattr(self.wrapped, "message_ports_out", None))
            and ports_out is not None and callable(ports_out)):
            for p in pmt.to_python(ports_out()):
                setattr(self, p, Port(p, tb, self, self.wrapped, PortDir.OUT, PortType.MSG))

        if ((sig_in:=getattr(self.wrapped, "input_signature", None))
            and sig_in is not None and callable(sig_in)):
            for i, sz in enumerate(sig_in().sizeof_stream_items()):
                self.inp.append(Port(i, tb, self, self.wrapped, PortDir.IN, PortType.STREAM, sz))

        if ((sig_out:=getattr(self.wrapped, "output_signature", None))
            and sig_out is not None and callable(sig_out)):
            for i, sz in enumerate(sig_out().sizeof_stream_items()):
                self.outp.append(Port(i, tb, self, self.wrapped, PortDir.OUT, PortType.STREAM, sz))


    def find_in_port(self, block):
        pass


    def __rshift__(self, rho):
        if type(rho) is D:
            rp = self.inp[0]
            assert(self.t == PortType.STREAM)
            assert(rp.t == PortType.STREAM)
            assert(rp.sz == self.sz)
            assert(rp.dir != self.dir)
        elif type(rho) is Port:
            rp = rho
        else:
            # Assume hier_block
            rp = rho
        print(self.outp[0].__dict__)
        lp = self.outp[0]
        lp >> rp
        return rho
