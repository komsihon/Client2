from threading import Thread
from django.http import HttpResponse
import json
from django.conf import settings

from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.http import urlquote
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

from ikwen.accesscontrol.forms import MemberForm, PasswordResetForm, SMSPasswordResetForm, SetPasswordForm, \
    SetPasswordFormSMSRecovery
from django.http.response import HttpResponseRedirect, HttpResponse, HttpResponseForbidden

from ikwen.accesscontrol.utils import invite_member
from ikwen.core.models import Service
from ikwen.core.constants import MALE, FEMALE
from ikwen.core.utils import get_service_instance, get_mail_content
from ikwen.accesscontrol.models import Member, DEFAULT_GHOST_PWD
from ikwen.revival.models import ProfileTag, MemberProfile, Revival
from ikwen.revival.utils import set_profile_tag_member_count
from ikwen.rewarding.models import Reward, ReferralRewardPack, CouponSummary, Coupon, CumulatedCoupon, CROperatorProfile
from ikwen.rewarding.utils import reward_member, JOIN
from ikwen.accesscontrol.backends import UMBRELLA
from ikwen_webnode.web.models import Banner, SLIDE, HomepageSection


class Home(TemplateView):
    template_name = 'webnode/improve/home.html'

    def get_context_data(self, **kwargs):
        context = super(Home, self).get_context_data(**kwargs)
        context['slideshow'] = Banner.objects.filter(display=SLIDE, is_active=True).order_by('order_of_appearance')
        context['homepage_section_list'] = HomepageSection.objects.filter(is_active=True).order_by('order_of_appearance')
        referrer_id = self.request.GET.get('referrer')
        member = self.request.user
        service = get_service_instance()

        coupon_qs = Coupon.objects.filter(status=Coupon.APPROVED, is_active=True)
        if member.is_authenticated():
            url = 'http://tchopetyamo.com/?referrer=' + member.id
            context['url'] = urlquote(url)
            coupon_list = []
            for coupon in coupon_qs:
                try:
                    cumul = CumulatedCoupon.objects.get(coupon=coupon, member=member)
                    coupon.count = cumul.count
                    coupon.ratio = float(cumul.count) / coupon.heap_size * 100
                except CumulatedCoupon.DoesNotExist:
                    coupon.count = 0
                    coupon.ratio = 0
                coupon_list.append(coupon)
            coupon_summary_list = member.couponsummary_set.filter(service=service)
            context['coupon_summary_list'] = coupon_summary_list
            context['coupon_list'] = coupon_list
        else:
            context['coupon_list'] = coupon_qs
        if referrer_id:
            try:
                referrer = Member.objects.get(pk=referrer_id)
            except Member.DoesNotExist:
                context['referrer'] = "Unknown user"
            else:
                context['referrer'] = referrer.get_short_name
        return context


def reward_referrer(request, *args, **kwargs):
    referrer_id = request.GET['referrer_id']
    member = request.user
    service = get_service_instance()
    if referrer_id:
        referrer = Member.objects.get(pk=referrer_id)
        referrer_profile, update = MemberProfile.objects.get_or_create(member=referrer)
        men_tag, update = ProfileTag.objects.get_or_create(name='Men', slug='men', is_reserved=True)
        women_tag, update = ProfileTag.objects.get_or_create(name='Women', slug='women', is_reserved=True)

        referrer_tag_fk_list = referrer_profile.tag_fk_list
        if men_tag.id in referrer_tag_fk_list:
            referrer_tag_fk_list.remove(men_tag.id)
        if women_tag.id in referrer_tag_fk_list:
            referrer_tag_fk_list.remove(women_tag.id)
        member_profile, update = MemberProfile.objects.get_or_create(member=member)
        member_profile.tag_fk_list.extend(referrer_tag_fk_list)
        if member.gender == MALE:
            member_profile.tag_fk_list.append(men_tag.id)
        elif member.gender == FEMALE:
            member_profile.tag_fk_list.append(women_tag.id)
        member_profile.save()
        referral_pack_list, coupon_count = reward_member(service, referrer, Reward.REFERRAL)
        if referral_pack_list:
            sender = 'Tchopetyamo <info@tchopetyamo.com>'
            referrer_subject = _("%s is offering you %d coupons for your referral to %s" % (service.project_name, coupon_count, member.full_name))
            template_name = 'rewarding/mails/referral_reward.html'
            CouponSummary.objects.using(UMBRELLA).get(service=service, member=referrer)
            html_content = get_mail_content(referrer_subject, template_name=template_name,
                                            extra_context={'referral_pack_list': referral_pack_list, 'coupon_count': coupon_count,
                                                           'joined_service': service, 'referee_name': member.full_name,
                                                           'joined_logo': service.config.logo})
            msg = EmailMessage(referrer_subject, html_content, sender, [referrer.email])
            msg.content_subtype = "html"
            Thread(target=lambda m: m.send(), args=(msg, )).start()


def save_ghost_user(request, *args, **kwargs):
    email = request.GET.get('email')
    service = get_service_instance()
    if email:
        try:
            member = Member.objects.filter(email=email)[0]
            response = {'error': _("Email already existing; Thanks for trying.")}
            invite_member(service, member)
            return HttpResponse(json.dumps({'response':  response}), 'content-type: text/json')
        except:
            pass

        username = email
        member = Member.objects.create_user(username, DEFAULT_GHOST_PWD, email=email, is_ghost=True)
        tag = JOIN
        join_tag, update = ProfileTag.objects.get_or_create(name=tag, slug=tag, is_auto=True)

        member_profile = MemberProfile.objects.get(member=member)
        member_profile.save()

        service = Service.objects.using(UMBRELLA).get(pk=getattr(settings, 'IKWEN_SERVICE_ID'))
        Revival.objects.using(UMBRELLA).get_or_create(service=service, model_name='core.Service', object_id=service.id,
                                                      mail_renderer='ikwen.revival.utils.render_suggest_create_account_mail',
                                                      profile_tag_id=join_tag.id, get_kwargs='ikwen.rewarding.utils.get_join_reward_pack_list')

        Thread(target=set_profile_tag_member_count).start()
        response = {'response': _("Email successful created. Thanks for your concern")}
        return HttpResponse(json.dumps({'response': response}), 'content-type: text/json')


class JoinGP(TemplateView):
    template_name = 'webnode/improve/join_gp.html'

    def get_context_data(self, **kwargs):
        context = super(JoinGP, self).get_context_data(**kwargs)
        return context


def join_gp_now(request, *args, **kwargs):
    member = request.user
    if request.user.is_authenticated():
        add_database_to_settings('gimipowa')
        try:
            Member.objects.using('gimipowa').get(username=member.username)
        except Member.DoesNotExist:
            member.save(using='gimipowa')
            next_url = reverse('shopping:home')
            final_url = '%s?gimipowa=joined'% (next_url)
        else:
            next_url = reverse('shopping:home')
            final_url = '%s?alreadyExist=yes'% (next_url)
    else:
        next_url = reverse('ikwen:sign_in')
        gp_url = reverse('join_gimipowa')
        final_url = '%s?next=%s'% (next_url, gp_url)
    return HttpResponseRedirect(final_url)
