import jwt
import requests

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView as _TemplateView
from onemsdk.parser import load_template
from onemsdk.schema.v1 import Response

from .models import Industry, User, Offer, History


class TemplateView(_TemplateView):
    @method_decorator(csrf_exempt)
    def dispatch(self, *a, **kw):
        return super(TemplateView, self).dispatch(*a, **kw)

    def get_user(self):
        # return User.objects.filter()[0]
        token = self.request.headers.get('Authorization')
        if token is None:
            raise PermissionDenied

        data = jwt.decode(token.replace('Bearer ', ''), key='87654321')
        user, created = User.objects.get_or_create(id=data['sub'])

        headers = {
            'X-API-KEY': settings.APP_APIKEY_POC,
            'Content-Type': 'application/json'
        }
        std_url = settings.RESTD_API_URL_POC.format(
            endpoint='users/{}'
        ).format(user.id)
        response = requests.get(url=std_url, headers=headers)
        if response.status_code == 200:
            response = response.json()
            if created:
                user.first_name = response['first_name']
                user.last_name = response['last_name']
            user.city = response['city']['name']
            user.country = response['city']['country']['name']
            user.save()

        return user

    def to_response(self, tag):
        response = Response.from_tag(tag)
        return HttpResponse(response.json(),
                            content_type='application/json')

    def get_user_counters(self):
        user = self.get_user()
        user_offers = user.offer_set.all()
        user_offers_ids = [user_offer.id for user_offer in user_offers]
        all_offers_count = Offer.objects.exclude(
            id__in=user_offers_ids
        ).count()
        profile_status = 0
        user_profile_attr = ['first_name', 'last_name', 'email']
        for attr in user_profile_attr:
            if getattr(user, attr):
                profile_status += 33
        user_offers_count = user.offer_set.count()
        user_history_count = user.history_set.count()
        user_offers = user.offer_set.all()
        user_views_count = 0
        if user_offers:
            all_history = History.objects.all()
            for user_offer in user_offers:
                for history_offer in all_history:
                    if user_offer.id == history_offer.accessed_offer.id:
                        user_views_count += 1
        data = {
            'all_offers_count': all_offers_count,
            'user_offers_count': user_offers_count,
            'user_views_count': user_views_count,
            'user_history_count': user_history_count,
            'profile_status': profile_status
        }
        return data


class HomeView(TemplateView):
    template_name = 'home.jinja2'
    http_method_names = ['get']

    def get(self, request):
        data = self.get_user_counters()
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AllOffersView(TemplateView):
    template_name = 'offers.jinja2'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'all',
            'items': []
        }
        all_offers = Offer.objects.all()
        if not all_offers:
            self.template_name = 'home.jinja2'
            data = self.get_user_counters()
            data['body_pre_items'] = ['No offers to show']
        else:
            user = self.get_user()
            user_offers = user.offer_set.all()
            if not user_offers:
                filtered_offers = all_offers
            else:
                user_offers_ids = [user_offer.id for user_offer in user_offers]
                filtered_offers = Offer.objects.exclude(id__in=user_offers_ids)
            if not filtered_offers:
                self.template_name = 'home.jinja2'
                data = self.get_user_counters()
                data['body_pre_items'] = ['No offers to show']

            else:
                for offer in filtered_offers:
                    data['items'].append({
                        'offer_id': offer.id,
                        'industry': offer.industry.industry_name,
                        'skill_description': offer.skill_description[:10]
                    })

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class OfferView(TemplateView):
    template_name = 'offer.jinja2'
    http_method_names = ['get']

    def get(self, request, id):
        offer = Offer.objects.get(pk=id)
        user = self.get_user()
        if not offer.id in [obj.accessed_offer.id for obj in user.history_set.all()]:
            history_create = History.objects.create(
                user=user, accessed_offer=offer
            )
            history_create.save()
        else:
            history_obj = [obj for obj in user.history_set.all()
                           if obj.accessed_offer.id == id][0]
            history_obj.date_accessed = timezone.now()
            history_obj.save()
        data = {
            'industry_name': offer.industry.industry_name,
            'skill_description': offer.skill_description,
            'offer_id': id,
            'user': offer.user.get_full_name()[:20] if offer.user.get_full_name() else
            'user_id {}'.format(offer.user.id)
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class MessageView(TemplateView):
    template_name = 'message.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request, id):
        data = {
            'offer_id': id,
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request, id):
        message = request.POST['message']
        user = self.get_user()
        offer = Offer.objects.get(pk=id)
        headers = {
            'X-API-KEY': settings.APP_APIKEY_POC,
            'Content-Type': 'application/json'
        }
        notify_url = settings.RESTD_API_URL_POC.format(
            endpoint='users/{}/notify'
        ).format(offer.user.id)
        user_full_name = user.get_full_name()
        body = {
            'header': 'skillhire - {}'.format(offer.skill_description[:10]),
            'body': '\n'.join([message, 'Sent by: {}'.format(
                user_full_name if user_full_name else user.id
            )]),
            'footer': 'Reply #skillhire'
        }
        response = requests.post(url=notify_url, json=body, headers=headers)
        if response.status_code == 200:
            self.template_name = 'home.jinja2'
            data = self.get_user_counters()
            data['body_pre_items'] = ['Your message was sent']
        else:
            self.template_name = 'std_menu.jinja2'
            message_response = 'Message not sent. Please try again later'
            data = {
                'header': 'offer details',
                'footer': 'Reply with A/BACK',
                'body_pre_items': [
                    message_response,
                    'Industry: {industry_name}'.format(
                        industry_name=offer.industry.industry_name
                    ),
                    offer.skill_description,
                ],
                'items': [{
                    'method': 'GET',
                    'href': '/message/{offer_id}'.format(offer_id=id),
                    'description': 'Send message to: {user}'.format(
                        user=offer.user.get_full_name()[:20] if offer.user.get_full_name() else
                            'user_id {}'.format(offer.user.id)
                    )
                }]
            }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class UserOffersView(TemplateView):
    template_name = 'offers.jinja2'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'your',
            'items': []
        }
        user = self.get_user()
        user_offers = user.offer_set.all()
        if user_offers:
            for offer in user_offers:
                data['items'].append({
                    'user_': 'user_',
                    'offer_id': offer.id,
                    'industry': offer.industry.industry_name,
                    'skill_description': offer.skill_description[:10]
                })
        else:
            self.template_name = 'home.jinja2'
            data = self.get_user_counters()
            data['body_pre_items'] = [
                'You have no offers. Reply C to add.'
            ]
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class UserOfferView(TemplateView):
    template_name = 'user_offer.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request, id):
        offer = Offer.objects.get(pk=id)
        data = {
            'offer_id': id,
            'skill_description': offer.skill_description
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request, id):
        offer = Offer.objects.get(pk=id)
        user = self.get_user()
        if request.POST['user_action'].lower() == 'delete':
            offer.delete()
            self.template_name = 'home.jinja2'
            data = self.get_user_counters()
            data['body_pre_items'] = ['Your skill offer has been deleted.']
        else:
            offer.skill_description = request.POST['user_action']
            offer.save()
            self.template_name = 'offers.jinja2'
            data = {
                'header': 'your',
                'body_pre_items': ['Your skill description has been changed.'],
                'items': []
            }
            updated_user_offers = user.offer_set.all()
            for offer in updated_user_offers:
                data['items'].append({
                    'user_': 'user_',
                    'offer_id': offer.id,
                    'industry': offer.industry.industry_name,
                    'skill_description': offer.skill_description[:10]
                })

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AddOfferView(TemplateView):
    template_name = 'add_offer.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request):
        industries = Industry.objects.all()
        data = {'industries': []}
        for industry in industries:
            data['industries'].append({
                'id': industry.id,
                'industry_name': industry.industry_name
            })

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        self.template_name = 'home.jinja2'
        offer_create = Offer.objects.create(
            user=self.get_user(),
            industry=Industry.objects.filter(
                pk=int(request.POST['industry_category'])
            )[0],
            skill_description=request.POST['skill_description']
        )
        offer_create.save()
        data = self.get_user_counters()
        data['body_pre_items'] = ['Offer added successfully']

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AllViewsView(TemplateView):
    template_name = 'std_wiz.jinja2'
    http_method_names = ['get']

    def get(self, request):
        user = self.get_user()
        user_offers = user.offer_set.all()
        data = self.get_user_counters()
        if not user_offers:
            self.template_name = 'home.jinja2'
            data['body_pre_items'] = ['You have no offers. Reply C to add.']
        elif data['user_views_count'] == 0:
            self.template_name = 'home.jinja2'
            data['body_pre_items'] = ['You have no views.']
        else:
            data = {
                'skip_confirmation': 'true',
                'method': 'GET',
                'action': '/',
                'header': 'your views',
                'footer': 'Reply BACK',
                'label_items': []
            }
            views_count = {}
            all_history = History.objects.all()
            for user_offer in user_offers:
                views_count[user_offer.skill_description[:15]] = 0
                for offer_from_history in all_history:
                    if user_offer.id == offer_from_history.accessed_offer.id:
                        views_count[user_offer.skill_description[:15]] += 1
            for k, v in views_count.items():
                data['label_items'].append('{}: {}'.format(k, v))

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class HistoryView(TemplateView):
    template_name = 'std_menu.jinja2'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'history',
            'footer': 'Select from history',
            'body_pre_items': [],
            'items': []
        }
        user = self.get_user()
        user_history = user.history_set.all().order_by('-date_accessed')
        if user_history:
            for obj in user_history:
                data['items'].append(
                    {'method': 'GET',
                     'href': '/offer/{offer_id}'.format(
                         offer_id=obj.accessed_offer.id
                     ),
                     'description': '{industry}: {offer_description}'.format(
                         industry=obj.accessed_offer.industry.industry_name,
                         offer_description=obj.accessed_offer.skill_description[:10]
                     )}
                )
        else:
            self.template_name = 'home.jinja2'
            data = self.get_user_counters()
            data['body_pre_items'] = ['No history to show']

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class ProfileView(TemplateView):
    template_name = 'profile.jinja2'
    http_method_names = ['get']

    def get(self, request):
        user = self.get_user()
        data = {
            'first_name': user.first_name if user.first_name else 'not set',
            'last_name': user.last_name if user.last_name else 'not set',
            'email': user.email if user.email else 'not set',
            'country': user.country if user.country else 'not set',
            'city': user.city if user.city else 'not set'
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


# class UsernameView(TemplateView):
#     template_name = 'std_wiz.jinja2'
#     http_method_names = ['get', 'post']

#     def get(self, request):
#         data = {
#             'skip_confirmation': 'true',
#             'method': 'POST',
#             'action': '/username/',
#             'header': 'set/change username',
#             'footer': 'Reply with username',
#             'label_items': ['150 characters or fewer. Letters, digits and '
#                             '@/./+/-/_ only.']
#         }
#         root_tag = load_template(template_file=self.template_name,
#                                  **data)
#         return self.to_response(root_tag)

#     def post(self, request):
#         user = self.get_user()
#         if not User.objects.filter(username__exact=str(request.POST['std_wiz'])):
#             user.username = str(request.POST['std_wiz'])
#             user.save()
#             body = 'Your username has been set.'
#         else:
#             body = 'Your username already exists! Try again with a different one.'
#         data = {
#             'header': 'confirmation',
#             'footer': 'Reply BACK',
#             'body': body,
#             'item': {'method': 'GET', 'href': '/profile/'}
#         }

#         root_tag = load_template(template_file='light_menu.jinja2'
#                                  **data)
#         return self.to_response(root_tag)


class FirstNameView(TemplateView):
    template_name = 'profile_change.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'action': '/first_name/',
            'profile_field': 'first name',
            'body_pre': '30 characters or fewer.'
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.first_name = request.POST['profile_change']
        user.save()
        self.template_name = 'profile.jinja2'
        data = {
            'body_pre': 'Your first name was changed',
            'first_name': user.first_name if user.first_name else 'not set',
            'last_name': user.last_name if user.last_name else 'not set',
            'email': user.email if user.email else 'not set',
            'country': user.country if user.country else 'not set',
            'city': user.city if user.city else 'not set'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class LastNameView(TemplateView):
    template_name = 'profile_change.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'action': '/last_name/',
            'profile_field': 'last name',
            'body_pre': '150 characters or fewer.'
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.last_name = request.POST['profile_change']
        user.save()
        self.template_name = 'profile.jinja2'
        data = {
            'body_pre': 'Your last name was changed',
            'first_name': user.first_name if user.first_name else 'not set',
            'last_name': user.last_name if user.last_name else 'not set',
            'email': user.email if user.email else 'not set',
            'country': user.country if user.country else 'not set',
            'city': user.city if user.city else 'not set'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class EmailView(TemplateView):
    template_name = 'profile_change.jinja2'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'action': '/email/',
            'profile_field': 'email',
            'body_pre': 'Enter a valid email address.'
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.email = request.POST['profile_change']
        user.save()
        self.template_name = 'profile.jinja2'
        data = {
            'body_pre': 'Your email address was changed',
            'first_name': user.first_name if user.first_name else 'not set',
            'last_name': user.last_name if user.last_name else 'not set',
            'email': user.email if user.email else 'not set',
            'country': user.country if user.country else 'not set',
            'city': user.city if user.city else 'not set'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class LocationView(TemplateView):
    template_name = 'std_wiz.jinja2'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'skip_confirmation': 'true',
            'method': 'GET',
            'action': '/profile/',
            'header': 'change location',
            'footer': 'Reply with #account',
            'label_items': ['To change your location details (country / city) '
                            'please go to #account service']
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)
