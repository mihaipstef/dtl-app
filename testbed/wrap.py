import inspect
import enum
import pmt
import typing as t


class PortDir(enum.Enum):
    IN = 0
    OUT = 1


class PortType(enum.Enum):
    MSG = 0
    STREAM = 1


class Port(object):

    id = None
    owner = None
    wrapped = None

    def __init__(self,
                 id: int|str,
                 tb: t.Any,
                 owner: t.Any,
                 wrapped: t.Any,
                 dir: t.Optional[PortDir],
                 t: t.Optional[PortType],
                 sz: t.Optional[int] = None):

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
            rp = HierPort(id, rho, rho)

        if self.t == PortType.MSG:
            self.tb.msg_connect(self.wrapped, self.id, rp.wrapped, rp.id)
        elif self.t == PortType.STREAM:
             self.tb.connect((self.wrapped, self.id), (rp.wrapped, rp.id))
        if type(rho) is Port:
            return rho.owner
        return rho


class HierPort(Port):
    def __init__(self, id, owner, wrapped):
        super().__init__(id, owner, owner, wrapped, None, None, None)



class D(object):

    exclude = set(["__class__"])

    wrapped: t.Any = None
    inp: t.List[Port] = []
    outp: t.List[Port] = []

    def __init__(self, tb: t.Any, w: t.Any, *args, **kwargs):
        if inspect.isclass(w):
            self.wrapped = w(*args, **kwargs)
        else:
            self.wrapped = w

        self.inp = []
        self.outp = []

        def make_proxy(name):
            def proxy(self):
                return getattr(self.wrapped, name)
            return proxy

        for name in dir(self.wrapped):
            if name not in self.exclude:
                if (a:=callable(getattr(self.wrapped, name))):
                    setattr(self, name, a)

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
            for i in range(sig_in().max_streams()):
                sz = sig_in().sizeof_stream_item(i)
                self.inp.append(Port(i, tb, self, self.wrapped, PortDir.IN, PortType.STREAM, sz))

        if ((sig_out:=getattr(self.wrapped, "output_signature", None))
            and sig_out is not None and callable(sig_out)):
            for i in range(sig_out().max_streams()):
                sz = sig_out().sizeof_stream_item(i)
                self.outp.append(Port(i, tb, self, self.wrapped, PortDir.OUT, PortType.STREAM, sz))


    def find_in_port(self, block):
        pass


    def __rshift__(self, rho):
        lp = self.outp[0]
        if type(rho) is D:
            rp = rho.inp[0]
            assert(lp.t == PortType.STREAM)
            assert(rp.t == PortType.STREAM)
            assert(rp.sz == lp.sz)
            assert(rp.dir != lp.dir)
        elif type(rho) is Port:
            rp = rho
            assert(rp.t == lp.t)
            assert(rp.sz == lp.sz)
            assert(rp.dir != lp.dir)
        else:
            # Assume hier_block
            rp = rho
        lp >> rp
        return rho
