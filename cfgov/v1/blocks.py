from wagtail.wagtailcore import blocks
from v1.util import util


class AbstractFormBlock(blocks.StructBlock):
    def get_result(self, page, request, value, is_submitted):
        handler_class = self.get_handler_class()
        handler = handler_class(page, request, block_value=value)
        return handler.process(is_submitted)

    def get_handler_class(self):
        handler_path = self.meta.handler
        if not handler_path:
            raise AttributeError('You must set a handler attribute on the ' +
                                 'Meta class.')
        return util.load_class(handler_path)

    def is_submitted(self, request, sfname, index):
        form_id = 'form-%s-%d' % (sfname, index)
        if request.method.lower() == self.meta.submit_method.lower():
            query_dict = getattr(request, self.meta.submit_method.upper())
            return form_id in query_dict.get('form_id', '')
        return False

    class Meta:
        # This should be a dotted path to the handler class for the block.
        handler = None
        submit_method = 'POST'
        icon = 'form'
