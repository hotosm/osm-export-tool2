# -*- coding: utf-8 -*-
import logging

from social_core import utils
from social_core.exceptions import InvalidEmail
from social_core.pipeline.partial import partial

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature
from django.urls import reverse
from django.shortcuts import redirect
from django.template.loader import get_template

LOG = logging.getLogger(__name__)


@partial
def require_email(strategy, backend, request, details, user=None, is_new=False, *args, **kwargs):  # pragma: no cover
    LOG.debug(user)
    if kwargs.get('ajax') or user and user.email:
        return
    elif is_new and not details.get('email'):
        email = strategy.request_data().get('email')
        if email:
            details['email'] = email
        else:
            return redirect('require_email')


def email_validation(strategy, backend, code, partial_token):  # pragma: no cover
    """
    Send an email with an embedded verification code and the necessary details to
    restore the required session elements to complete the verification and sign-in,
    regardless of what browser the user completes the verification from.
    """
    signature = signing.dumps({"session_key": strategy.session.session_key, "email": code.email},
                              key=settings.SECRET_KEY)
    verifyURL = "{0}?verification_code={1}&signature={2}&partial_token={3}".format(
        reverse('osm:complete', args=(backend.name,)),
        code.code,
        signature,
        partial_token
    )
    verifyURL = strategy.request.build_absolute_uri(verifyURL)
    ctx = {
            'verifyUrl': verifyURL,
    }
    subject = "Please verify your email address"
    text = get_template('osm/verify_osm_email.txt').render(ctx)
    html = get_template('osm/verify_osm_email.html').render(ctx)
    msg = EmailMultiAlternatives(
        subject, text, to=[code.email], from_email="HOT Export Tool <exports@hotosmmail.org>"
    )
    msg.attach_alternative(html, "text/html")
    msg.send()

    # clear out the redirect URL since it probably doesn't matter (and may have
    # been an OAuth redirect)
    strategy.session_pop("next")


def partial_pipeline_data(backend, user=None, *args, **kwargs):  # pragma: no cover
    """
    Add the session key to a signed base64 encoded signature on the email request.
    """
    data = backend.strategy.request_data()
    if 'signature' in data:
        try:
            signed_details = signing.loads(data['signature'], key=settings.SECRET_KEY)
            session = Session.objects.get(pk=signed_details['session_key'])
        except (BadSignature, Session.DoesNotExist) as e:
            raise InvalidEmail(backend)

        session_details = session.get_decoded()
        backend.strategy.session_set('email_validation_address', session_details['email_validation_address'])
        backend.strategy.session_set('next', session_details.get('next'))
        backend.strategy.session_set('partial_pipeline', session_details['partial_pipeline'])
        backend.strategy.session_set(backend.name + '_state', session_details.get(backend.name + '_state'))
        backend.strategy.session_set(backend.name + 'unauthorized_token_name',
                                     session_details.get(backend.name + 'unauthorized_token_name'))

    partial = backend.strategy.session_get('partial_pipeline', None)
    if partial:
        idx, backend_name, xargs, xkwargs = \
            backend.strategy.partial_from_session(partial)
        if backend_name == backend.name:
            kwargs.setdefault('pipeline_index', idx)
            if user:  # don't update user if it's None
                kwargs.setdefault('user', user)
            kwargs.setdefault('request', backend.strategy.request_data())
            xkwargs.update(kwargs)
            return xargs, xkwargs
        else:
            backend.strategy.clean_partial_pipeline()


utils.partial_pipeline_data = partial_pipeline_data
