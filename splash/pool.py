from twisted.internet import defer

class RenderPool(object):
    """A pool of renders. The number of slots determines how many
    renders will be run in parallel, at the most."""

    def __init__(self, slots, network_manager, get_splash_proxy_factory):
        self.network_manager = network_manager
        self.get_splash_proxy_factory = get_splash_proxy_factory
        self.active = set()
        self.queue = defer.DeferredQueue()
        for n in range(slots):
            self._wait_for_render(None, n)

    def render(self, rendercls, request, *args):
        extdef = defer.Deferred()
        if self.get_splash_proxy_factory:
            splash_proxy_factory = self.get_splash_proxy_factory(request)
        else:
            splash_proxy_factory = None
        self.queue.put((rendercls, request, splash_proxy_factory, args, extdef))
        return extdef

    def _wait_for_render(self, _, slot):
        d = self.queue.get()
        d.addCallback(self._start_render)
        d.addBoth(self._wait_for_render, slot)
        return _

    def _start_render(self, (rendercls, request, splash_proxy_factory, args, extdef)):
        render = rendercls(
            network_manager=self.network_manager,
            splash_proxy_factory=splash_proxy_factory,
            splash_request=request,
        )
        render.doRequest(*args)
        self.active.add(render)
        d = render.deferred
        d.addBoth(self._close_render, render)
        d.chainDeferred(extdef)
        return d

    def _close_render(self, _, render):
        self.active.remove(render)
        render.close()
        return _