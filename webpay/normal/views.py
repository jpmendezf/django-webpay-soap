# !/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import traceback
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .communication import WebpayNormalWS
from .models import WebpayNormal

logger = logging.getLogger(__name__)


def webpay_normal_model(get_normal_transaction):
    """
    Metodo que ayudara a guardar el modelo de manera correcta y enviar signals
    a la app Django.
    """
    webpaymodel = WebpayNormal.objects.get(
        buyOrder=get_normal_transaction['buyOrder'],
        transactionDate__isnull=True)
    webpaymodel.sessionId = get_normal_transaction['sessionId']
    webpaymodel.cardNumber = get_normal_transaction.cardDetail['cardNumber']
    webpaymodel.accountingDate = get_normal_transaction['accountingDate']
    webpaymodel.transactionDate = get_normal_transaction['transactionDate']
    webpaymodel.authorizationCode = get_normal_transaction.detailOutput[0]['authorizationCode']
    webpaymodel.paymentTypeCode = get_normal_transaction.detailOutput[0]['paymentTypeCode']
    webpaymodel.responseCode = get_normal_transaction.detailOutput[0]['responseCode']
    webpaymodel.amount = int(get_normal_transaction.detailOutput[0]['amount'])
    webpaymodel.sharesNumber = get_normal_transaction.detailOutput[0]['sharesNumber']
    webpaymodel.commerceCode = get_normal_transaction.detailOutput[0]['commerceCode']
    webpaymodel.save()
    webpaymodel.send_signals()
    return webpaymodel


@csrf_exempt
def webpay_normal_verificacion(request):
    """
    Vista que sera consultada por metodo POST por Transbank para entregarnos
    el token del estado de una transaccion.
    """
    token = request.POST.get("token_ws")
    logger.debug("Data recibida por Transbank {}".format(request))
    if token:
        try:
            get_normal_transaction = WebpayNormalWS().getTransaction(token)
            webpaymodel = webpay_normal_model(get_normal_transaction)
            logger.debug('Pago BuyOrder {}. Respuesta {}'.format(
                webpaymodel.buyOrder,
                webpaymodel.responseCode))
            # Informamos a Tranbank la correcta recepcion. Si no se informa
            # entonces transbank reversa la transaccion.
            WebpayNormalWS().acknowledgeTransaction(token)
            # Haremos un response del Token que nos envia Transbank y haremos un
            # automatico redirect con JS
            response = """
                <body background="https://webpay3g.transbank.cl/webpayserver/imagenes/background.gif">
                    <form action='{}' method='post' id='webpay_form'>
                        <input type='hidden' name='token_ws' value='{}'>
                    </form>
                    <script>document.getElementById('webpay_form').submit();</script>
                </body>
            """.format(get_normal_transaction['urlRedirection'], token)
            return HttpResponse(response)
        except Exception, e:
            logger.error('Ocurrio un error al consultar Token enviado por Transbank. Error {} Traza {}'.format(
                e, traceback.format_exc()))
    return HttpResponseBadRequest()


@csrf_exempt
def webpay_normal_termina(request):
    """
    Vista generica que ayuda a recibir el ultimo paramtero de Transbank
    """
    token = request.POST.get("token_ws")
    response = None
    if token:
        webpaymodel = WebpayNormal.objects.get(token=token)
        response = "Transaccion {} exitosa de la Orden de compra {}".format(
            "" if token else "NO", webpaymodel.buyOrder)
    return HttpResponse(response)
