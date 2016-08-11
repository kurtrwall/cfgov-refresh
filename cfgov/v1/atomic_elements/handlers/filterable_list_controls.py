from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from ... import forms
from ...handlers import Handler
from ...models import CFGOVPage, AbstractFilterPage, EventPage
from ...util.ref import choices_for_page_type
from ...util.util import has_active_filters


class GenericHandler(Handler):
    def process(self, block_value, form_id):
        form = self._get_form(form_id)
        results_limit = block_value.get('results_limit', 10)
        posts = self._process_filters(form, results_limit)

        self.context['form'] = form
        self.context['posts'] = posts

        if 'has_active_filters' not in self.context:
            self.context['has_active_filters'] = has_active_filters

    def _get_form(self, form_id):
        form_class = self._get_filter_form_class()
        form_data = self._process_form_data(form_class, form_id)
        form = form_class(form_data, parent=self.page.parent(),
                          hostname=self.request.site.hostname)
        return form

    @staticmethod
    def _get_filter_form_class():
        return forms.FilterableListForm

    def _process_form_data(self, form_class, form_id):
        fields = getattr(form_class, 'declared_fields', {})
        data = {}
        for field in fields:
            request_field_name = 'filter' + str(form_id) + '_' + field
            if field in ['categories', 'topics', 'authors']:
                data[field] = self.request.GET.getlist(request_field_name, [])
            else:
                data[field] = self.request.GET.get(request_field_name, '')
        return data

    def _process_filters(self, form, results_limit):
        if form.is_valid():
            page_set = self.get_page_set(form)
            paginator = Paginator(page_set, results_limit)
            page = self.request.GET.get('page')

            # Get the page number in the request and get the page from the
            # paginator to serve.
            try:
                posts = paginator.page(page)
            except PageNotAnInteger:
                posts = paginator.page(1)
            except EmptyPage:
                posts = paginator.page(paginator.num_pages)

        else:
            empty_page_set = CFGOVPage.objects.none()
            paginator = Paginator(empty_page_set, results_limit)
            posts = paginator.page(1)

        return posts

    def get_page_set(self, form):
        query = form._generate_query()
        page_set = AbstractFilterPage.objects.child_of(self.page).filter(query)
        page_set = page_set.live_shared(self.request.site.hostname).distinct()
        return page_set.order_by('-date_published')


class EventArchiveHandler(GenericHandler):
    def get_page_set(self, form):
        query = form._generate_query()
        page_set = EventPage.objects.child_of(self.page).filter(query)
        page_set = page_set.live_shared(self.request.site.hostname).distinct()
        return page_set.order_by('-date_published')

    @staticmethod
    def _get_filter_form_class():
        return forms.EventArchiveFilterForm


class NewsroomHandler(GenericHandler):
    def get_page_set(self, form):
        categories = form.cleaned_data.get('categories', [])
        query = self._get_page_queries(form, categories)
        page_set = AbstractFilterPage.objects.filter(query).distinct()
        page_set = page_set.live_shared(self.request.site.hostname)
        return page_set.order_by('-date_published')

    def _get_page_queries(self, form, categories):
        get_blog, only_blog = self._if_and_only_blog(categories)
        newsroom_q = self._get_newsroom_query(form) if not only_blog else Q()
        blog_q = self._get_blog_query(form) if get_blog else Q()
        return newsroom_q | blog_q

    @staticmethod
    def _if_and_only_blog(categories):
        get_blog = True
        only_blog = False
        if categories:
            if 'blog' not in categories:
                get_blog = False
            else:
                if len(categories) == 1:
                    only_blog = True
        return get_blog, only_blog

    def _get_newsroom_query(self, form):
        newsroom_q = AbstractFilterPage.objects.child_of_q(self.page)
        return newsroom_q & form._generate_query()

    def _get_blog_query(self, form):
        try:
            del form.cleaned_data['categories']
            blog = CFGOVPage.objects.get(slug='blog')
            blog_q = AbstractFilterPage.objects.child_of_q(blog)
            return blog_q & form._generate_query()
        except CFGOVPage.DoesNotExist:
            return form._generate_query()

    @staticmethod
    def _get_filter_form_class():
        return forms.NewsroomFilterForm


class ActivityLogHandler(GenericHandler):
    def get_page_set(self, form):
        queries = {}
        selections = {}
        categories = form.cleaned_data.get('categories', [])
        orig_categories = list(categories)
        
        selections = self._process_categories(categories)
        self._set_newsroom_query(form, categories, orig_categories, queries)
        self._set_blog_and_report_queries(form, selections, queries)
    
        return self._process_queries(queries)

    # Set filter selections for Blog and Report and process categories
    @staticmethod
    def _process_categories(categories):
        selections = {'blog': False, 'research-reports': False}
        for category in selections.keys():
            if not categories or category in categories:
                selections[category] = True
        for selection, is_selected in selections.items():
            if is_selected and selection in categories:
                del categories[categories.index(selection)]
        return selections

    # Set Newsroom query if one or more Newsroom categories are selected
    @staticmethod
    def _set_newsroom_query(form, categories, orig_categories, queries):
        choices = [c[0] for c in choices_for_page_type('newsroom')]
        is_newsroom_category = bool(map(lambda x: x in choices, categories))
        if not orig_categories or is_newsroom_category:
            try:
                parent = CFGOVPage.objects.get(slug='newsroom')
                query = AbstractFilterPage.objects.child_of_q(parent)
                queries['newsroom'] = query & form._generate_query()
            except CFGOVPage.DoesNotExist:
                print 'Newsroom page does not exist'

    # Set Blog and Report queries if they were selected
    @staticmethod
    def _set_blog_and_report_queries(form, selections, queries):
        del form.cleaned_data['categories']
        for slug, is_selected in selections.items():
            if is_selected:
                try:
                    parent = CFGOVPage.objects.get(slug=slug)
                    query = AbstractFilterPage.objects.child_of_q(parent)
                    queries.update({
                        slug: query & form._generate_query()
                    })
                except CFGOVPage.DoesNotExist as e:
                    print slug, 'does not exist'

    # OR all selected queries together
    def _process_queries(self, queries):
        final_q = reduce(lambda x, y: x | y, queries.values())
        page_set = AbstractFilterPage.objects.filter(final_q)
        page_set = page_set.live_shared(self.request.site.hostname).distinct()
        return page_set.order_by('-date_published')

    @staticmethod
    def _get_filter_form_class():
        return forms.ActivityLogFilterForm
