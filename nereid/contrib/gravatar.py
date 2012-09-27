# -*- coding: UTF-8 -*-
'''
    gravatar

    Helpers to work with gravatar.com
'''
import hashlib
import urllib

from nereid import request


def url(email, **kwargs):
    """
    Return a gravatar url for the given email

    :param https: To get a secure URL
    :param default: The default image to return if there is no profile pic
                    For example a unisex avatar
    :param size: The size for the image
    """
    if kwargs.get('https', request.scheme == 'https'):
        url = 'https://secure.gravatar.com/avatar/%s?'
    else:
        url = 'http://www.gravatar.com/avatar/%s?'
    url = url % hashlib.md5(email.lower()).hexdigest()

    params = []
    default = kwargs.get('default', None)
    if default:
        params.append(('d', default))

    size = kwargs.get('size', None)
    if size:
        params.append(('s', str(size)))

    return url + urllib.urlencode(params)
