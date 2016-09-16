from itertools import chain
from wagtail.wagtailcore.blocks.stream_block import StreamValue


class Handler(object):
    def __init__(self, page, request, context={}):
        self.page = page
        self.request = request
        self.context = context

    def process(self):
        raise NotImplementedError
