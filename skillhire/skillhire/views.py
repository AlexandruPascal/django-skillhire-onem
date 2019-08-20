import jwt
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView as _TemplateView
from onemsdk.config import set_static_dir
from onemsdk.parser import load_template
from onemsdk.schema.v1 import Response

from .models import Offer, History


class TemplateView(_TemplateView):
    set_static_dir('skillhire/skillhire/templates')

    @method_decorator(csrf_exempt)
    def dispatch(self, *a, **kw):
        return super(TemplateView, self).dispatch(*a, **kw)

    def get_user(self):
        # return User.objects.filter()[0]
        token = self.request.headers.get('Authorization')
        if token is None:
            raise PermissionDenied

        data = jwt.decode(token.replace('Bearer ', ''), key='87654321')
        user, created = User.objects.get_or_create(id=data['sub'],
                                                   username=str(data['sub']))
        return user

    def to_response(self, tag):
        response = Response.from_tag(tag)
        return HttpResponse(response.json(),
                            content_type='application/json')


class HomeView(TemplateView):
    template_name = 'std_menu.html'
    http_method_names = ['get']

    def get(self, request):
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
            'header': 'home',
            'footer': 'Reply A-F',
            'body_pre': '',
            'items': [
                {
                    'method': 'GET',
                    'href': '/all_offers',
                    'description': 'All offers ({all_offers_count})'.format(
                        all_offers_count=all_offers_count
                    )
                },
                {
                    'method': 'GET',
                    'href': '/user_offers',
                    'description': 'Your offers ({user_offers_count})'.format(
                        user_offers_count=user_offers_count
                    )
                },
                {
                    'method': 'GET',
                    'href': '/add_offer',
                    'description': 'Add offer'
                },
                {
                    'method': 'GET',
                    'href': '/all_views',
                    'description': 'Views ({user_views_count})'.format(
                        user_views_count=user_views_count
                    )
                },
                {
                    'method': 'GET',
                    'href': '/history',
                    'description': 'History ({user_history_count})'.format(
                        user_history_count=user_history_count
                    )
                },
                {
                    'method': 'GET',
                    'href': '/profile',
                    'description': 'Profile {profile_status}%'.format(
                        profile_status=profile_status
                    )
                },
            ]
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AllOffersView(TemplateView):
    template_name = 'std_menu.html'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'all offers',
            'footer': 'Select offer',
            'body_pre': '',
            'items': []
        }
        all_offers = Offer.objects.all()
        if not all_offers:
            self.template_name = 'std_wiz.html'
            data = {
                'confirmation_needed': 'false',
                'method': 'GET',
                'action': '/',
                'header': 'all offers',
                'footer': 'Reply BACK',
                'label': 'No offers to show',
            }
        else:
            user = self.get_user()
            user_offers = user.offer_set.all()
            if not user_offers:
                filtered_offers = all_offers
            else:
                user_offers_ids = [user_offer.id for user_offer in user_offers]
                filtered_offers = Offer.objects.exclude(id__in=user_offers_ids)
            if not filtered_offers:
                data['footer'] = 'Reply BACK'
                data['items'].append({'method': 'GET',
                                      'href': '/',
                                      'description': 'No offers to show'})

            else:
                for offer in filtered_offers:
                    data['items'].append(
                        {'method': 'GET',
                         'href': '/offer/{offer_id}'.format(
                             offer_id=offer.id
                         ),
                         'description': 'Offer: {offer_description}'.format(
                             offer_description=offer.description[:10]
                         )}
                    )

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class OfferView(TemplateView):
    template_name = 'std_menu.html'
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
            'header': 'offer details',
            'footer': 'Reply with A',
            'body_pre': offer.description,
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


class MessageView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request, id):
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/message/{offer_id}'.format(offer_id=id),
            'header': 'message',
            'footer': 'Reply with text/BACK',
            'label': 'Reply with your message for the offer owner',
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request, id):
        message = request.POST['std_wiz']
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
            'header': 'skillhire - {}'.format(offer.description[:10]),
            'body': u'\n'.join([message, 'Sent by: {}'.format(
                user_full_name if user_full_name else user.id
            )]),
            'footer': 'Reply #skillhire'
        }
        response = requests.post(url=notify_url, json=body, headers=headers)
        if response.status_code == 200:
            message_sent = 'Your message was sent'
        else:
            message_sent = 'Message not sent. Please try again later'
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/offer/{offer_id}'.format(offer_id=id),
            'header': 'offer detail',
            'footer': 'Reply BACK',
            'label': u'\n'.join([message_sent, offer.description]),
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class UserOffersView(TemplateView):
    template_name = 'std_menu.html'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'your offers',
            'footer': 'Select offer',
            'body_pre': '',
            'items': []
        }
        user = self.get_user()
        user_offers = user.offer_set.all()
        if user_offers:
            for offer in user_offers:
                data['items'].append(
                    {'method': 'GET',
                     'href': '/user_offer/{offer_id}'.format(
                         offer_id=offer.id
                     ),
                     'description': 'Offer: {offer_description}'.format(
                         offer_description=offer.description[:10]
                     )}
                )
        else:
            self.template_name = 'std_wiz.html'
            data = {
                'confirmation_needed': 'false',
                'method': 'GET',
                'action': '/',
                'header': 'your offers',
                'footer': 'Reply BACK',
                'label': 'No offers to show',
            }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class UserOfferView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request, id):
        offer = Offer.objects.get(pk=id)
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/user_offer/{offer_id}/'.format(offer_id=id),
            'header': 'change description',
            'footer': 'Reply with text/BACK',
            'label': u'\n'.join([
                'Current description: {offer_description};'.format(
                    offer_description=offer.description
                ),
                'New description must have 40 characters or fewer.'
            ]),
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request, id):
        offer = Offer.objects.get(pk=id)
        offer.description = request.POST['std_wiz']
        offer.save()
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/user_offers/',
            'header': 'confirmation',
            'footer': 'Reply BACK',
            'label': 'Your description has been changed.'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AddOfferView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/add_offer/',
            'header': 'add offer',
            'footer': 'Reply with text',
            'label': 'Describe your skill. 40 characters or fewer.',
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        offer_create = Offer.objects.create(
            user=self.get_user(), description=request.POST['std_wiz']
        )
        offer_create.save()
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/',
            'header': 'confirmation',
            'footer': 'Reply BACK',
            'label': 'Your offer has been added'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class AllViewsView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/',
            'header': 'your views',
            'footer': 'Reply BACK',
            'label': None
        }
        user = self.get_user()
        user_offers = user.offer_set.all()
        if user_offers:
            views_count = {}
            all_history = History.objects.all()
            for user_offer in user_offers:
                views_count[user_offer.description[:10]] = 0
                for offer_from_history in all_history:
                    if user_offer.id == offer_from_history.accessed_offer.id:
                        views_count[user_offer.description[:10]] += 1
            labels = []
            for k, v in views_count.items():
                labels.append('{}: {}'.format(k, v))

            data['label'] = u'\n'.join(labels)
        else:
            data['label'] = 'You have no offers'

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class HistoryView(TemplateView):
    template_name = 'std_menu.html'
    http_method_names = ['get']

    def get(self, request):
        data = {
            'header': 'history',
            'footer': 'Select from history',
            'body_pre': '',
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
                     'description': 'Offer: {offer_description}'.format(
                         offer_description=obj.accessed_offer.description[:10]
                     )}
                )
        else:
            self.template_name = 'std_wiz.html'
            data = {
                'confirmation_needed': 'false',
                'method': 'GET',
                'action': '/',
                'header': 'history',
                'footer': 'Reply BACK',
                'label': 'No history to show',
            }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class ProfileView(TemplateView):
    template_name = 'user_profile.html'
    http_method_names = ['get']

    def get(self, request):
        user = self.get_user()
        data = {
            'header': 'profile',
            'footer': 'Reply A-D',
            'first_name': {
                'method': 'GET',
                'href': '/first_name',
                'description': 'First name: {first_name}'.format(
                    first_name=user.first_name if user.first_name else 'not set'
                )
            },
            'last_name': {
                'method': 'GET',
                'href': '/last_name',
                'description': 'Last name: {last_name}'.format(
                    last_name=user.last_name if user.last_name else 'not set'
                )
            },
            'email': {
                'method': 'GET',
                'href': '/email',
                'description': 'Email: {email}'.format(
                    email=user.email if user.email else 'not set'
                )
            },
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


# class UsernameView(TemplateView):
#     template_name = 'std_wiz.html'
#     http_method_names = ['get', 'post']

#     def get(self, request):
#         data = {
#             'confirmation_needed': 'false',
#             'method': 'POST',
#             'action': '/username/',
#             'header': 'set/change username',
#             'footer': 'Reply with username',
#             'label': '150 characters or fewer. '
#                      'Letters, digits and @/./+/-/_ only.',
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

#         root_tag = load_template(template_file='light_menu.html'
#                                  **data)
#         return self.to_response(root_tag)


class FirstNameView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/first_name/',
            'header': 'set/change first name',
            'footer': 'Reply with first name',
            'label': '30 characters or fewer.',
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.first_name = request.POST['std_wiz']
        user.save()
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/profile/',
            'header': 'confirmation',
            'footer': 'Reply BACK',
            'label': 'Your first name has been set.'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class LastNameView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/last_name/',
            'header': 'set/change last name',
            'footer': 'Reply with last name',
            'label': '150 characters or fewer.',
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.last_name = request.POST['std_wiz']
        user.save()
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/profile/',
            'header': 'confirmation',
            'footer': 'Reply BACK',
            'label': 'Your last name has been set.'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)


class EmailView(TemplateView):
    template_name = 'std_wiz.html'
    http_method_names = ['get', 'post']

    def get(self, request):
        data = {
            'confirmation_needed': 'false',
            'method': 'POST',
            'action': '/email/',
            'header': 'set/change email',
            'footer': 'Reply with email address',
            'label': 'Enter a valid email address.',
        }
        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)

    def post(self, request):
        user = self.get_user()
        user.email = request.POST['std_wiz']
        user.save()
        data = {
            'confirmation_needed': 'false',
            'method': 'GET',
            'action': '/profile/',
            'header': 'confirmation',
            'footer': 'Reply BACK',
            'label': 'Your email address has been set.'
        }

        root_tag = load_template(template_file=self.template_name,
                                 **data)
        return self.to_response(root_tag)
