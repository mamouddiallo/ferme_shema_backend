from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """
    Limite les tentatives de connexion, indépendamment de la limite générale
    des utilisateurs anonymes. Basé sur l'IP (comme AnonRateThrottle), pas
    sur le username tenté — sinon un attaquant pourrait épuiser le quota
    d'un compte légitime pour bloquer son propriétaire (déni de service).
    """

    scope = "login"
